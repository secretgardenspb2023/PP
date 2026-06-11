"""Rebuild the Elasticsearch plants index from the database (ТЗ Этап 5.3)."""
from django.core.management.base import BaseCommand

from apps.catalog import search
from apps.catalog.models import Plant


class Command(BaseCommand):
    help = "Drop and rebuild the Elasticsearch plants index from the database."

    def handle(self, *args, **options):
        queryset = (
            Plant.objects.select_related("species__genus__family", "description")
            .prefetch_related("synonyms")
        )
        self.stdout.write("reindexing…")
        count = search.reindex(queryset)
        self.stdout.write(self.style.SUCCESS(f"indexed {count} plants into '{search.INDEX}'"))
