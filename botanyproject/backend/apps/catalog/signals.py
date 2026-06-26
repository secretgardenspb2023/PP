"""Авто-синхронизация карточек с Elasticsearch (ТЗ 5.20).

При сохранении/удалении растения через админку (или код) ES-индекс обновляется
сразу — без полного реиндекса. Операция в ES выполняется ПОСЛЕ коммита транзакции
(transaction.on_commit), чтобы при откате в индексе не осталось «фантома», и
обёрнута в try/except — сбой ES не должен ломать сохранение/удаление в админке.

Массовые операции (es_reindex, bulk_update в backfill_names) идут через bulk и
.update() — сигналы там НЕ срабатывают, поэтому лишней нагрузки нет.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import search
from .models import Plant

logger = logging.getLogger("apps.catalog.signals")

_PLANT_QS = Plant.objects.select_related("species__genus__family").prefetch_related(
    "synonyms", "species__synonyms", "species__genus__synonyms"
)


@receiver(post_save, sender=Plant)
def index_plant_on_save(sender, instance, **kwargs):
    pk = instance.pk

    def _do():
        try:
            search.index_plant(_PLANT_QS.get(pk=pk))
        except Plant.DoesNotExist:
            pass
        except Exception:  # noqa: BLE001 — сбой ES не ломает сохранение карточки
            logger.warning("ES: не удалось проиндексировать карточку %s", pk, exc_info=True)

    transaction.on_commit(_do)


@receiver(post_delete, sender=Plant)
def deindex_plant_on_delete(sender, instance, **kwargs):
    pk = instance.pk

    def _do():
        try:
            search.delete_plant(pk)
        except Exception:  # noqa: BLE001 — сбой ES не ломает удаление карточки
            logger.warning("ES: не удалось убрать карточку %s из индекса", pk, exc_info=True)

    transaction.on_commit(_do)
