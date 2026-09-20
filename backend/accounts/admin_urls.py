from django.urls import path

from .admin_views import (
    AdminUserActivateView,
    AdminUserDeactivateView,
    AdminUserDetailView,
    AdminUserListView,
    AdminUserResendInviteView,
)

# เส้นทางของ Admin ทั้งหมดอยู่ใต้ /api/admin/ (ดู config/urls.py) — เฉพาะผู้ใช้บทบาท admin เรียกได้
urlpatterns = [
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path(
        "users/<int:pk>/deactivate/",
        AdminUserDeactivateView.as_view(),
        name="admin-user-deactivate",
    ),
    path("users/<int:pk>/activate/", AdminUserActivateView.as_view(), name="admin-user-activate"),
    path(
        "users/<int:pk>/resend-invite/",
        AdminUserResendInviteView.as_view(),
        name="admin-user-resend-invite",
    ),
]
