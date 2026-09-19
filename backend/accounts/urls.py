from django.urls import path

from .views import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordCheckView,
    ResetPasswordView,
    VerifyEmailView,
)

# เส้นทางทั้งหมดอยู่ใต้ /api/auth/ (ดู config/urls.py)
urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="auth-resend-verification"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/check/", ResetPasswordCheckView.as_view(), name="auth-reset-check"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
]
