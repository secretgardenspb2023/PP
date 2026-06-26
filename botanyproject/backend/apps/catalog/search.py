"""Elasticsearch indexing + search for the catalog (ТЗ Этап 5.3–5.11).

Uses the stock `elasticsearch` client (no plugins): the built-in Russian snowball
stemmer gives morphology-aware matching (посадка↔посадить), an edge-ngram analyzer
powers instant autosuggest, and fuzzy multi_match handles typos. Synonyms are
indexed per-plant from `plant_synonyms`. Callers fall back to PostgreSQL when ES
is unavailable (see views). A fuller lemmatizer (analysis-morphology / hunspell)
can be added to the ES image later without changing this interface.
"""
from django.conf import settings as dj_settings
from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import bulk

INDEX = "plants"

INDEX_BODY = {
    "settings": {
        "analysis": {
            # Сворачиваем ё/э → е (и в индексе, и в запросе): данные часто пишут
            # «Алое» вместо «Алоэ», «клен» вместо «клён» — так запрос «алоэ»/«клён»
            # находит карточку независимо от е/ё/э.
            "char_filter": {
                "ru_eyo": {"type": "mapping", "mappings": ["ё=>е", "Ё=>е", "э=>е", "Э=>е"]},
            },
            "filter": {
                "ru_stop": {"type": "stop", "stopwords": "_russian_"},
                "ru_stemmer": {"type": "stemmer", "language": "russian"},
                "edge_ngram": {"type": "edge_ngram", "min_gram": 2, "max_gram": 20},
            },
            "analyzer": {
                "ru": {
                    "char_filter": ["ru_eyo"],
                    "tokenizer": "standard",
                    "filter": ["lowercase", "ru_stop", "ru_stemmer"],
                },
                "ru_suggest_index": {
                    "char_filter": ["ru_eyo"],
                    "tokenizer": "standard",
                    "filter": ["lowercase", "edge_ngram"],
                },
                "ru_suggest_search": {
                    "char_filter": ["ru_eyo"],
                    "tokenizer": "standard",
                    "filter": ["lowercase"],
                },
            },
        }
    },
    "mappings": {
        "properties": {
            "id_plant": {"type": "integer"},
            "url_slug": {"type": "keyword"},
            "name_rus": {"type": "text", "analyzer": "ru"},
            # Каноническое отображаемое имя карточки (заполнено для всех, включает сорт).
            "rus_name_unique": {"type": "text", "analyzer": "ru"},
            # Canonical Russian binomial assembled from taxonomy (genus + species
            # rus_name) — populated even when plants.name_rus is blank (~11%).
            "name_rus_full": {"type": "text", "analyzer": "ru"},
            "lat_name": {"type": "text", "analyzer": "standard"},
            "species": {"type": "text", "analyzer": "standard"},
            "species_rus": {"type": "text", "analyzer": "ru"},
            "genus": {"type": "text", "analyzer": "standard"},
            "genus_rus": {"type": "text", "analyzer": "ru"},
            "family": {"type": "text", "analyzer": "ru"},
            "synonyms": {"type": "text", "analyzer": "ru"},
            "description": {"type": "text", "analyzer": "ru"},
            "usda_zone": {"type": "integer"},
            "suggest": {
                "type": "text",
                "analyzer": "ru_suggest_index",
                "search_analyzer": "ru_suggest_search",
            },
        }
    },
}

# Поиск идёт по названиям/синонимам/таксономии — НЕ по тексту описания.
# Матч по описанию + fuzzy давал ложные совпадения («алое» → красные клёны
# из-за «алый» в описании, «ель» → пихты). Описание остаётся в индексе (для
# подсветки), но в подбор результатов не входит.
SEARCH_FIELDS = [
    "rus_name_unique^5", "name_rus^5", "name_rus_full^5", "synonyms^4", "lat_name^3",
    "genus^2", "genus_rus^2", "species_rus^2", "family^2",
    "species",
]


# Таблица опечаток — ОТДЕЛЬНО от ботанических синонимов (по просьбе заказчика).
# Частые ошибки/варианты написания → каноническое слово. Применяется к тексту
# запроса ДО поиска. Пополняется свободно; реиндекс НЕ нужен. Ключи в нижнем регистре.
TYPO_FIXES = {
    "спатифилум": "спатифиллум",
    "стапифилум": "спатифиллум",
    "спатифиллюм": "спатифиллум",
    "спацифилум": "спатифиллум",
}


def fix_typos(query):
    """Заменить известные опечатки в словах запроса на канонические написания."""
    return " ".join(TYPO_FIXES.get(w.lower(), w) for w in (query or "").split())


# Поля для префиксного поиска по частичному последнему слову (только названия).
PREFIX_FIELDS = ["rus_name_unique^5", "name_rus_full^5", "name_rus^4", "lat_name^3"]


def _match_query(query):
    """Тело ES-запроса. Для многословных запросов добавляем phrase_prefix — ищем по
    ЧАСТИ последнего слова («Клематис гибридный Ma» → «…Madame…»). Для одного слова —
    точное совпадение (чтобы «роза» не цепляла «розовый»)."""
    base = {
        "multi_match": {
            "query": query, "fields": SEARCH_FIELDS,
            "type": "best_fields", "fuzziness": "AUTO:5,8", "operator": "and",
        }
    }
    if len(query.split()) > 1:
        return {
            "bool": {
                "should": [
                    base,
                    {"multi_match": {"query": query, "fields": PREFIX_FIELDS, "type": "phrase_prefix"}},
                ],
                "minimum_should_match": 1,
            }
        }
    return base


def get_client():
    return Elasticsearch(dj_settings.ELASTICSEARCH_URL, request_timeout=10)


def is_available(client=None):
    try:
        return (client or get_client()).ping()
    except Exception:  # noqa: BLE001
        return False


def build_document(plant):
    species = plant.species
    genus = species.genus
    family = genus.family
    description = getattr(plant, "description", None)
    # Синонимы всех уровней (род + вид + растение) — как в карточке. Большинство
    # синонимов в базе на уровне рода/вида; раньше индексировались только plant-level,
    # из-за чего поиск по синониму почти не работал.
    synonyms = [
        s.full_name or s.synonym_name
        for s in (*genus.synonyms.all(), *species.synonyms.all(), *plant.synonyms.all())
        if (s.full_name or s.synonym_name)
    ]
    name_rus = plant.name_rus or ""
    rus_name_unique = plant.rus_name_unique or ""
    lat_name = plant.lat_name_unique or ""
    genus_rus = genus.rus_name or ""
    species_rus = species.rus_name or ""
    # Canonical Russian binomial ("Дуб черешчатый") — the searchable Russian name
    # even when plants.name_rus is blank. Lets a "дуб черешчатый" query match in a
    # single field under best_fields + operator=and.
    name_rus_full = " ".join(filter(None, [genus_rus, species_rus]))
    return {
        "_index": INDEX,
        "_id": plant.id_plant,
        "id_plant": plant.id_plant,
        "url_slug": plant.url_slug,
        "name_rus": name_rus,
        "rus_name_unique": rus_name_unique,
        "name_rus_full": name_rus_full,
        "lat_name": lat_name,
        "species": species.name,
        "species_rus": species_rus,
        "genus": genus.name or "",
        "genus_rus": genus_rus,
        "family": family.family_lat if family else "",
        "synonyms": synonyms,
        "description": (description.content_text if description else "") or "",
        "usda_zone": plant.usda_zone,
        # Russian name (explicit + taxonomic) + latin + synonyms feed autosuggest (ТЗ 5.6/5.7)
        "suggest": " ".join(filter(None, [rus_name_unique, name_rus, name_rus_full, lat_name, *synonyms])),
    }


def _document_body(plant):
    """Тело документа для одиночной индексации (без _index/_id, которые нужны bulk)."""
    return {k: v for k, v in build_document(plant).items() if k not in ("_index", "_id")}


def index_plant(plant, *, client=None):
    """Проиндексировать/обновить одну карточку в ES (для авто-синхронизации сигналами)."""
    (client or get_client()).index(index=INDEX, id=plant.id_plant, document=_document_body(plant))


def delete_plant(id_plant, *, client=None):
    """Убрать карточку из индекса ES; 404 (уже нет) — игнорируем."""
    try:
        (client or get_client()).delete(index=INDEX, id=id_plant)
    except NotFoundError:
        pass


def reindex(queryset, *, client=None, chunk_size=1000):
    """Drop and rebuild the index from a Plant queryset. Returns indexed count."""
    client = client or get_client()
    if client.indices.exists(index=INDEX):
        client.indices.delete(index=INDEX)
    client.indices.create(index=INDEX, body=INDEX_BODY)
    indexed, _ = bulk(
        client,
        (build_document(p) for p in queryset.iterator(chunk_size=chunk_size)),
        chunk_size=chunk_size,
        request_timeout=120,
    )
    client.indices.refresh(index=INDEX)
    return indexed


def search(query, *, size=24, offset=0, client=None):
    client = client or get_client()
    query = fix_typos(query)
    body = {
        "from": offset,
        "size": size,
        "query": _match_query(query),
        "highlight": {
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
            "fields": {"name_rus": {}, "synonyms": {}, "description": {"fragment_size": 150}},
        },
    }
    resp = client.search(index=INDEX, body=body)
    hits = resp["hits"]
    return {
        "count": hits["total"]["value"],
        "results": [
            {
                "id_plant": h["_source"]["id_plant"],
                "url_slug": h["_source"]["url_slug"],
                "name": (h["_source"].get("rus_name_unique") or h["_source"]["name_rus"]
                         or h["_source"].get("name_rus_full") or h["_source"]["lat_name"]),
                "lat_name": h["_source"]["lat_name"],
                "family": h["_source"]["family"],
                "score": h["_score"],
                "highlight": h.get("highlight", {}),
            }
            for h in hits["hits"]
        ],
    }


def search_ids(query, *, limit=10000, client=None):
    """Return id_plant values matching ``query``, ordered by relevance.

    Used by the catalog list/facets so full-text search (morphology, typos,
    «ё/е», synonyms, descriptions) runs through Elasticsearch while filtering,
    faceting, sorting and pagination stay in PostgreSQL. ``limit`` is capped at
    the index ``max_result_window`` (10k); the catalog holds ~12k cards and a
    text query realistically matches far fewer.
    """
    client = client or get_client()
    query = fix_typos(query)
    body = {
        "from": 0,
        "size": limit,
        "_source": False,
        "query": _match_query(query),
    }
    resp = client.search(index=INDEX, body=body)
    return [int(h["_id"]) for h in resp["hits"]["hits"]]


def suggest(query, *, size=10, client=None):
    client = client or get_client()
    query = fix_typos(query)
    body = {
        "size": size,
        "_source": ["id_plant", "url_slug", "rus_name_unique", "name_rus", "name_rus_full", "lat_name"],
        "query": {"match": {"suggest": {"query": query, "operator": "and"}}},
    }
    resp = client.search(index=INDEX, body=body)
    return [
        {
            "id_plant": h["_source"]["id_plant"],
            "url_slug": h["_source"]["url_slug"],
            "name": (h["_source"].get("rus_name_unique") or h["_source"]["name_rus"]
                     or h["_source"].get("name_rus_full") or h["_source"]["lat_name"]),
        }
        for h in resp["hits"]["hits"]
    ]
