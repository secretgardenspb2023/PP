from django.conf import settings
from django.core.cache import cache
from django.db import connections
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness/readiness probe (ТЗ Этап 2.8).

    Checks DB, Redis, Elasticsearch and (when configured) S3. Returns 200 when
    all critical dependencies are healthy, otherwise 503 with per-check detail.
    """

    authentication_classes: list = []
    permission_classes: list = []
    throttle_classes: list = []

    @extend_schema(summary="Проверка состояния сервиса", responses={200: dict, 503: dict})
    def get(self, request):
        checks = {
            "database": self._check_database(),
            "redis": self._check_redis(),
            "elasticsearch": self._check_elasticsearch(),
            "s3": self._check_s3(),
        }
        critical = ("database", "redis", "elasticsearch")
        healthy = all(checks[name] == "ok" for name in critical)
        code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=code,
        )

    @staticmethod
    def _check_database():
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return f"error: {exc.__class__.__name__}"

    @staticmethod
    def _check_redis():
        try:
            cache.set("health:ping", "1", timeout=5)
            return "ok" if cache.get("health:ping") == "1" else "error: no echo"
        except Exception as exc:  # noqa: BLE001
            return f"error: {exc.__class__.__name__}"

    @staticmethod
    def _check_elasticsearch():
        try:
            from elasticsearch import Elasticsearch

            client = Elasticsearch(settings.ELASTICSEARCH_URL, request_timeout=2)
            return "ok" if client.ping() else "error: no ping"
        except Exception as exc:  # noqa: BLE001
            return f"error: {exc.__class__.__name__}"

    @staticmethod
    def _check_s3():
        if not (settings.AWS_ACCESS_KEY_ID and settings.AWS_STORAGE_BUCKET_NAME):
            return "not_configured"
        try:
            import boto3

            client = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return f"error: {exc.__class__.__name__}"
