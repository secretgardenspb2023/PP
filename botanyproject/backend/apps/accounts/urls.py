from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("token/refresh/", views.TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password/reset/", views.PasswordResetView.as_view(), name="password-reset"),
    path(
        "password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/socials/", views.SocialAccountsView.as_view(), name="socials"),
    path("me/sessions/", views.SessionsView.as_view(), name="sessions"),
    path("2fa/setup/", views.TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("2fa/confirm/", views.TwoFactorConfirmView.as_view(), name="2fa-confirm"),
    path("2fa/disable/", views.TwoFactorDisableView.as_view(), name="2fa-disable"),
    path("2fa/status/", views.TwoFactorStatusView.as_view(), name="2fa-status"),
    path("google/", views.GoogleLoginView.as_view(), name="google"),
    path("google/callback/", views.GoogleCallbackView.as_view(), name="google-callback"),
    path("telegram/", views.TelegramLoginView.as_view(), name="telegram"),
    path("vk/", views.VKLoginView.as_view(), name="vk"),
    path("vk/callback/", views.VKCallbackView.as_view(), name="vk-callback"),
]
