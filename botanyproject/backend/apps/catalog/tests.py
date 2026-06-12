"""Regression tests for catalog search indexing (ТЗ Этап 5).

`build_document` is a pure mapping over a Plant + its taxonomy, so we exercise it
with lightweight stubs — no DB, no Elasticsearch. Guards the Russian-search fix:
when ``plants.name_rus`` is blank (~11% of the catalog) the card must still be
findable and shown by its canonical Russian binomial (genus + species rus_name).
"""
from types import SimpleNamespace

from apps.catalog.search import build_document
from apps.catalog.serializers import PlantDetailSerializer


def _plant(*, name_rus, genus_rus, species_rus, genus_lat="Quercus",
           species_lat="robur", lat_name="Quercus robur"):
    family = SimpleNamespace(family_lat="Fagaceae", family_rus="Буковые")
    genus = SimpleNamespace(name=genus_lat, rus_name=genus_rus, family=family)
    species = SimpleNamespace(name=species_lat, rus_name=species_rus, genus=genus)
    return SimpleNamespace(
        id_plant=9760, url_slug="quercus-robur", species=species,
        name_rus=name_rus, lat_name_unique=lat_name, usda_zone=5,
        synonyms=SimpleNamespace(all=lambda: []),
        description=None,
    )


def test_russian_binomial_indexed_when_name_rus_blank():
    """Blank name_rus must not lose the Russian name: taxonomy fills name_rus_full."""
    doc = build_document(_plant(name_rus="", genus_rus="Дуб", species_rus="черешчатый"))

    assert doc["genus_rus"] == "Дуб"
    assert doc["species_rus"] == "черешчатый"
    assert doc["name_rus_full"] == "Дуб черешчатый"
    # autosuggest must carry the Russian binomial so "дуб череш" matches
    assert "Дуб черешчатый" in doc["suggest"]
    # latin genus is indexed separately (not overwritten by the Russian name)
    assert doc["genus"] == "Quercus"


def test_explicit_name_rus_preserved():
    """An explicit name_rus is kept alongside the taxonomic Russian name."""
    doc = build_document(_plant(name_rus="Дуб обыкновенный", genus_rus="Дуб",
                                species_rus="черешчатый"))
    assert doc["name_rus"] == "Дуб обыкновенный"
    assert doc["name_rus_full"] == "Дуб черешчатый"
    assert "Дуб обыкновенный" in doc["suggest"]


def _syn(name, *, is_binomial=False):
    return SimpleNamespace(synonym_name=name, full_name=name, synonym_lang="lat",
                           synonym_type="basionym", is_binomial=is_binomial)


def _plant_with_synonyms(*, genus_syn, species_syn, plant_syn):
    genus = SimpleNamespace(synonyms=SimpleNamespace(all=lambda: genus_syn))
    species = SimpleNamespace(genus=genus,
                              synonyms=SimpleNamespace(all=lambda: species_syn))
    return SimpleNamespace(species=species,
                           synonyms=SimpleNamespace(all=lambda: plant_syn))


def test_synonyms_inherited_from_genus_and_species():
    """Card synonyms inherit genus- and species-level (binomial) entries, tagged
    by level, alongside plant-level ones (matrix: синонимы уровня род и род-вид)."""
    plant = _plant_with_synonyms(
        genus_syn=[_syn("Quercus L.")],
        species_syn=[_syn("Quercus robur L.", is_binomial=True)],
        plant_syn=[_syn("Quercus pedunculata")],
    )
    result = PlantDetailSerializer().get_synonyms(plant)

    by_level = {r["level"]: r for r in result}
    assert set(by_level) == {"genus", "species", "plant"}
    assert by_level["genus"]["synonym_name"] == "Quercus L."
    assert by_level["species"]["is_binomial"] is True
    assert by_level["plant"]["synonym_name"] == "Quercus pedunculata"


def test_synonyms_empty_when_no_links():
    plant = _plant_with_synonyms(genus_syn=[], species_syn=[], plant_syn=[])
    assert PlantDetailSerializer().get_synonyms(plant) == []
