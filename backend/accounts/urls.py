from django.urls import path

from .views import LoginView, LogoutView, MeView, RefreshView

# เส้นทางทั้งหมดอยู่ใต้ /api/auth/ (ดู config/urls.py)
urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
]
