"""Custom User bound to the client's existing ``user_info.users`` table.

ТЗ Этап 3.1/3.2: the project's user model is the client-owned ``user_info.users``
(not a Django-generated table). The table is ``managed = False`` — Django reads
and writes rows but does not own the schema; the ``'schema"."table'`` quoting
trick makes Django emit ``"user_info"."users"`` (same pattern as ``apps.catalog``).

Django-auth needs four columns the original table lacks — ``is_active`` (gates
unverified emails), ``is_staff`` / ``is_superuser`` (admin + permissions) and
``last_login``. They are added by migration ``0003`` (ALTER TABLE) and seeded
from ``role_id``. Everything else maps onto existing columns: ``password`` →
``password_hash``, ``date_joined`` → ``created_at``. ``full_name`` is a property
over ``first_name``/``last_name`` so the API contract stays unchanged.

See docs/database.md (раздел «Решения») for the agreed mapping.
"""
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager

# user_info.dict_roles ids (see dump / docs/database.md).
ROLE_ADMIN = 1
ROLE_MODERATOR = 2
ROLE_DEFAULT = 5  # «Пользователь» — роль самостоятельно зарегистрировавшихся.

# Canonical social_provider values allowed by the table CHECK constraint
# (∈ {VK, TG, Гугл, Макс}). Keep code in sync with that constraint.
PROVIDER_GOOGLE = "Гугл"
PROVIDER_TELEGRAM = "TG"
PROVIDER_VK = "VK"  # на будущее (VK-вход отложен — нет ключей приложения)


class DictRole(models.Model):
    """Read-only mapping of ``user_info.dict_roles`` (роли пользователей)."""

    role_name = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'user_info"."dict_roles'
        verbose_name = _("роль")
        verbose_name_plural = _("роли")

    def __str__(self):
        return self.role_name


class User(AbstractBaseUser):
    """User bound to ``user_info.users`` (email is the login identifier).

    The client's table has its own role system (``role_id`` → dict_roles), so we
    deliberately do NOT use Django's ``PermissionsMixin`` (groups/user_permissions
    M2M). Admin/permissions run off ``is_superuser``/``is_staff``; granular
    moderator permissions are Фаза 2.
    """

    id = models.AutoField(primary_key=True)
    # Real columns of user_info.users.
    first_name = models.CharField(_("имя"), max_length=100)
    last_name = models.CharField(_("фамилия"), max_length=100, blank=True, null=True)
    email = models.EmailField(_("email"), max_length=150, unique=True)
    login = models.CharField(_("логин"), max_length=50, unique=True)
    nickname = models.CharField(_("ник"), max_length=50, unique=True, blank=True, null=True)
    phone = models.CharField(_("телефон"), max_length=20, unique=True, blank=True, null=True)
    avatar_url = models.TextField(_("аватар"), blank=True, null=True)
    # password lives in column ``password_hash`` (varchar 255).
    password = models.CharField(_("пароль"), max_length=255, db_column="password_hash")
    # social_provider CHECK ∈ {VK, TG, Гугл, Макс}; пусто = NULL (а не '', иначе CHECK падает).
    social_provider = models.CharField(_("соц-провайдер"), max_length=20, blank=True, null=True, default=None)
    social_id = models.CharField(_("соц-ID"), max_length=100, blank=True, null=True, default=None)
    store_name = models.CharField(_("магазин"), max_length=150, blank=True, null=True)
    role = models.ForeignKey(
        DictRole, on_delete=models.RESTRICT, db_column="role_id", verbose_name=_("роль")
    )
    city_id = models.IntegerField(_("город"), blank=True, null=True)
    district_id = models.IntegerField(_("район"), blank=True, null=True)
    date_joined = models.DateTimeField(_("дата регистрации"), db_column="created_at", auto_now_add=True)

    # Columns added by migration 0003 (ALTER TABLE) for Django auth/admin.
    # ``last_login`` (nullable) comes from AbstractBaseUser and is also added there.
    is_active = models.BooleanField(_("активен"), default=True)
    is_staff = models.BooleanField(_("доступ в админку"), default=False)
    is_superuser = models.BooleanField(_("суперпользователь"), default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        managed = False
        db_table = 'user_info"."users'
        verbose_name = _("пользователь")
        verbose_name_plural = _("пользователи")

    def __str__(self):
        return self.email

    # -- full_name keeps the API/admin contract while the table stores parts -- #
    @property
    def full_name(self):
        return " ".join(filter(None, [self.first_name, self.last_name])).strip()

    @full_name.setter
    def full_name(self, value):
        self.first_name = (value or "").strip()
        self.last_name = ""

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.first_name

    # -- Minimal permission interface (superuser bypass; no Django groups) -- #
    def has_perm(self, perm, obj=None):
        return self.is_active and self.is_superuser

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        return self.is_active and self.is_superuser

    # NOT NULL columns (login/first_name/role) must always be populated, no matter
    # which path creates the row (manager, admin add-form, oauth). Fill them here.
    def save(self, *args, **kwargs):
        if not self.login:
            self.login = type(self).objects.make_login(self.email)
        if not self.first_name:
            self.first_name = (self.email or "user").split("@")[0][:100]
        if self.role_id is None:
            self.role_id = ROLE_DEFAULT
        super().save(*args, **kwargs)
