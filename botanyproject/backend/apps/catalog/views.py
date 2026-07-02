"""Catalog read-API (ТЗ Этап 5)."""
import hashlib
from urllib.parse import urlencode

from django.core.cache import cache
from django.db.models import Prefetch, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import imgproxy, media
from . import models as m
from . import search as es
from .filters import (
    DIMENSIONS, RANGES, SORTS, apply_filters, facet_counts, histograms,
)
from .serializers import PlantDetailSerializer, PlantListSerializer, ReviewSerializer

SEARCH_PAGE_SIZE = 24


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

# relation accessor -> link model, prefetched with its dictionary value
_LINK_RELATIONS = {
    "leaf_shapes": m.PlantLeafShape,
    "habit_forms": m.PlantHabitForm,
    "flower_forms": m.PlantFlowerForm,
    "sun_types": m.PlantSunType,
    "soil_acidity": m.PlantSoilAcidity,
    "propagation_methods": m.PlantPropagation,
    "care_levels": m.PlantCareLevel,
    "design_uses_m2m": m.PlantDesignUse,
    "garden_styles_m2m": m.PlantGardenStyle,
    "designers": m.PlantDesigner,
    "fruit_uses_m2m": m.PlantFruitUse,
    "flower_colors_m2m": m.PlantFlowerColor,
    "leaf_colors_m2m": m.PlantLeafColor,
    "vegetation_periods_m2m": m.PlantVegetationPeriod,
    "flowering_months_m2m": m.PlantFloweringMonth,
    "fruiting_months_m2m": m.PlantFruitingMonth,
}


def _detail_queryset():
    prefetches = [
        Prefetch(name, queryset=model.objects.select_related("value"))
        for name, model in _LINK_RELATIONS.items()
    ]
    return (
        m.Plant.objects.select_related(
            "species__genus__family", "visual", "care", "design", "description"
        )
        # synonyms inherited from three taxonomic levels (matrix) — prefetch each
        .prefetch_related(
            "photos", "synonyms", "species__synonyms", "species__genus__synonyms",
            *prefetches,
        )
    )


_FILTER_PARAMS = [
    OpenApiParameter("q", str, description="Текстовый поиск по названиям и таксономии."),
    OpenApiParameter("sort", str, description=f"Сортировка: {', '.join(SORTS)}."),
    OpenApiParameter("usda_zone", str, description="Зоны USDA через запятую (OR)."),
    OpenApiParameter("category", str, description="Категории по зоне: garden (1-5), seasonal (6-8), indoor (9+); через запятую."),
    *[
        OpenApiParameter(dim, str, description="Несколько значений через запятую (OR).")
        for dim in DIMENSIONS
    ],
    *[
        OpenApiParameter(f"{prefix}_{bound}", int, description=f"{field} ({bound}).")
        for prefix, field in RANGES.items()
        for bound in ("min", "max")
    ],
]


class PlantViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Список карточек с фасетными фильтрами и детальная карточка растения."""

    # ЧПУ-слаги могут содержать точки (из инициалов, напр. «h.e.» в «H.E. Bealle»).
    # DRF по умолчанию запрещает точки в lookup (regex [^/.]+) → 404. Разрешаем.
    lookup_value_regex = "[^/]+"

    def get_serializer_class(self):
        return PlantDetailSerializer if self.action == "retrieve" else PlantListSerializer

    def get_object(self):
        """Открываем карточку по url_slug (ЧПУ) или по числовому id. Слаги почти
        уникальны (несколько дублей) — для дубля берём карточку с меньшим id."""
        from django.http import Http404

        lookup = str(self.kwargs.get("pk", ""))
        qs = self.get_queryset()
        if lookup.isdigit():
            obj = qs.filter(id_plant=lookup).first()
        else:
            obj = qs.filter(url_slug=lookup).order_by("id_plant").first()
        if obj is None:
            raise Http404("Растение не найдено")
        return obj

    def get_queryset(self):
        if self.action == "retrieve":
            return _detail_queryset()
        qs = m.Plant.objects.select_related("species__genus__family").prefetch_related("photos")
        qs = apply_filters(qs, self.request.query_params).distinct()
        sort = SORTS.get(self.request.query_params.get("sort", ""), "id_plant")
        return qs.order_by(sort)

    @extend_schema(parameters=_FILTER_PARAMS)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        parameters=_FILTER_PARAMS,
        description="Счётчики фасетных фильтров с учётом остальных активных фильтров.",
    )
    @action(detail=False)
    def facets(self, request):
        # Facets are the heaviest query (16 grouped counts) — cache in Redis with
        # a short TTL (ТЗ 5.20). Read-only catalog, so TTL expiry is enough; add
        # explicit invalidation once card editing lands (этап 7).
        params = sorted(request.query_params.items())
        key = "facets:" + hashlib.md5(urlencode(params).encode()).hexdigest()  # noqa: S324
        data = cache.get(key)
        if data is None:
            data = facet_counts(m.Plant.objects.all(), request.query_params)
            cache.set(key, data, timeout=600)
        return Response(data)

    @extend_schema(description="Список url_slug всех карточек для карты сайта (sitemap.xml).")
    @action(detail=False)
    def sitemap(self, request):
        # Лёгкий список слагов + дата для генерации sitemap.xml фронтом (SEO, этап 8).
        data = cache.get("sitemap_slugs")
        if data is None:
            seen = {}
            for slug, created in (
                m.Plant.objects.exclude(url_slug__isnull=True).exclude(url_slug="")
                .values_list("url_slug", "created_at")
            ):
                seen.setdefault(slug, created)  # дедуп по слагу (есть дубли карточек)
            data = [{"slug": s, "updated": c} for s, c in seen.items()]
            cache.set("sitemap_slugs", data, timeout=3600)
        return Response(data)

    @extend_schema(
        parameters=_FILTER_PARAMS,
        description="Гистограммы распределения диапазонных фильтров (высота, диаметр, "
        "прирост) с учётом остальных активных фильтров (ТЗ 5.14).",
    )
    @action(detail=False)
    def histograms(self, request):
        params = sorted(request.query_params.items())
        key = "histograms:" + hashlib.md5(urlencode(params).encode()).hexdigest()  # noqa: S324
        data = cache.get(key)
        if data is None:
            data = histograms(m.Plant.objects.all(), request.query_params)
            cache.set(key, data, timeout=600)
        return Response(data)


class SearchView(APIView):
    """Полнотекстовый поиск (Elasticsearch: морфология + опечатки + синонимы,
    подсветка). При недоступности ES — fallback на PostgreSQL ILIKE (ТЗ 5.11)."""

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, required=True, description="Поисковый запрос."),
            OpenApiParameter("page", int, description="Страница (по 24)."),
        ],
        responses={200: dict},
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"count": 0, "results": [], "engine": "none"})
        page = max(1, _int(request.query_params.get("page"), 1))
        offset = (page - 1) * SEARCH_PAGE_SIZE

        if es.is_available():
            try:
                data = es.search(query, size=SEARCH_PAGE_SIZE, offset=offset)
                data["engine"] = "elasticsearch"
                return Response(data)
            except Exception:  # noqa: BLE001 — degrade to PostgreSQL
                pass
        return Response(self._pg_fallback(query, offset))

    @staticmethod
    def _pg_fallback(query, offset):
        qs = (
            m.Plant.objects.select_related("species__genus__family")
            .prefetch_related("photos")
            .filter(
                Q(name_rus__icontains=query)
                | Q(lat_name_unique__icontains=query)
                | Q(rus_name_unique__icontains=query)
                | Q(species__name__icontains=query)
                | Q(synonyms__synonym_name__icontains=query)
            )
            .distinct()
        )
        count = qs.count()
        page = qs[offset:offset + SEARCH_PAGE_SIZE]
        return {
            "count": count,
            "results": PlantListSerializer(page, many=True).data,
            "engine": "postgresql",
        }


class SuggestView(APIView):
    """Мгновенные автоподсказки (edge-ngram). Fallback на PostgreSQL prefix."""

    @extend_schema(
        parameters=[OpenApiParameter("q", str, required=True)],
        responses={200: dict},
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])
        if es.is_available():
            try:
                return Response(es.suggest(query))
            except Exception:  # noqa: BLE001
                pass
        qs = m.Plant.objects.filter(
            Q(name_rus__istartswith=query) | Q(lat_name_unique__istartswith=query)
        )[:10]
        return Response(
            [
                {"id_plant": p.id_plant, "url_slug": p.url_slug,
                 "name": p.name_rus or p.lat_name_unique}
                for p in qs
            ]
        )


class ReviewListCreateView(APIView):
    """Отзывы к растению (ТЗ §11 Фаза 2). GET — одобренные отзывы; POST — создать
    (нужна авторизация), текст + до 5 фото, статус «на модерации»."""

    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "reviews"
    MAX_PHOTOS = 5

    def get_throttles(self):
        # Лимит частоты (10/час) — только на создание; чтение остаётся свободным.
        return [ScopedRateThrottle()] if self.request.method == "POST" else super().get_throttles()

    def get(self, request, plant_id):
        qs = (
            m.Review.objects.filter(plant_id=plant_id, status="approved")
            .prefetch_related("photos")
        )
        return Response({"count": qs.count(), "results": ReviewSerializer(qs, many=True).data})

    def post(self, request, plant_id):
        if not m.Plant.objects.filter(id_plant=plant_id).exists():
            return Response({"detail": "Растение не найдено."}, status=status.HTTP_404_NOT_FOUND)
        # Один отзыв на растение от пользователя — защита от спама одной карточки.
        if m.Review.objects.filter(plant_id=plant_id, user=request.user).exists():
            return Response(
                {"detail": "Вы уже оставляли отзыв к этому растению."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        text = (request.data.get("text") or "").strip()
        if len(text) < 3:
            return Response({"text": ["Напишите текст отзыва."]}, status=status.HTTP_400_BAD_REQUEST)

        # Отзыв администратора публикуется сразу, без модерации (ТЗ-доработка).
        is_admin = bool(request.user.is_staff or request.user.is_superuser)
        review = m.Review.objects.create(
            plant_id=plant_id,
            user=request.user,
            author_name=(getattr(request.user, "full_name", "") or request.user.email or "Пользователь"),
            text=text[:5000],
            status="approved" if is_admin else "pending",
        )
        errors = []
        for f in request.FILES.getlist("photos")[: self.MAX_PHOTOS]:
            try:
                key = media.upload_image(
                    f.read(), f.content_type, prefix="reviews",
                    max_bytes=media.REVIEW_MAX_BYTES,
                )
                m.ReviewPhoto.objects.create(
                    review=review, storage_key=key,
                    public_url=imgproxy.full(key), preview_url=imgproxy.thumb(key),
                )
            except ValueError as exc:
                errors.append(str(exc))
        detail = (
            "Отзыв опубликован." if is_admin
            else "Спасибо! Отзыв отправлен на модерацию."
        )
        return Response(
            {"detail": detail, "id": review.id, "status": review.status,
             "photo_errors": errors},
            status=status.HTTP_201_CREATED,
        )
