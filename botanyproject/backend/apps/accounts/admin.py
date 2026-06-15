from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import UserChangeForm, UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    filter_horizontal = ()  # no Django groups/user_permissions on this model
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "role")
    search_fields = ("email", "first_name", "last_name", "login")
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "login", "password")}),
        (_("Личные данные"), {"fields": ("first_name", "last_name", "nickname", "phone", "role")}),
        (
            _("Права"),
            {"fields": ("is_active", "is_staff", "is_superuser")},
        ),
        (_("Важные даты"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
