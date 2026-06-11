from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user with email as the login identifier (ТЗ Этап 2.3 / 3.1).

    NOTE: per ТЗ Этап 3 this model will be re-bound to the client's existing
    ``user_info.users`` table once that schema dump is delivered (the dump
    received so far only contains the ``plant_info`` schema). Until then it uses
    a managed table so the project boots and migrates cleanly. To switch later:

        class Meta:
            db_table = 'user_info"."users'
            managed = False  # if the table is owned by the client's DB
    """

    email = models.EmailField(_("email"), unique=True)
    full_name = models.CharField(_("полное имя"), max_length=255, blank=True)
    # Linked social account (ТЗ Этап 3.5/3.6). Maps to user_info.users.social_*
    # when the model is later rebound to the client's table.
    social_provider = models.CharField(_("соц-провайдер"), max_length=20, blank=True, default="")
    social_id = models.CharField(_("соц-ID"), max_length=128, blank=True, default="")
    is_active = models.BooleanField(_("активен"), default=True)
    is_staff = models.BooleanField(_("доступ в админку"), default=False)
    date_joined = models.DateTimeField(_("дата регистрации"), default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("пользователь")
        verbose_name_plural = _("пользователи")
        constraints = [
            models.UniqueConstraint(
                fields=["social_provider", "social_id"],
                condition=~models.Q(social_id=""),
                name="uq_user_social_account",
            ),
        ]

    def __str__(self):
        return self.email
