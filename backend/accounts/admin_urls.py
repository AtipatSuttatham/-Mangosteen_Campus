from django.urls import path

from .admin_views import AdminUserDetailView, AdminUserListView

# เส้นทางของ Admin ทั้งหมดอยู่ใต้ /api/admin/ (ดู config/urls.py) — เฉพาะผู้ใช้บทบาท admin เรียกได้
urlpatterns = [
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
]
