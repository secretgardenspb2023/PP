from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for the email-based user bound to ``user_info.users``."""

    use_in_migrations = True

    def make_login(self, email):
        """Generate a unique ``login`` (NOT NULL, uniq, ≤50) from the email."""
        base = (self.normalize_email(email or "").split("@")[0] or "user")[:40]
        login = base
        suffix = 1
        while self.filter(login=login).exists():
            suffix += 1
            login = f"{base}-{suffix}"[:50]
        return login

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Поле email обязательно")
        email = self.normalize_email(email)
        extra_fields.setdefault("login", self.make_login(email))
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        # «Администратор» role (id 1) + Django admin/permissions flags.
        from .models import ROLE_ADMIN

        extra_fields.setdefault("role_id", ROLE_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")
        return self._create_user(email, password, **extra_fields)
