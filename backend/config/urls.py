"""URL หลักของโปรเจกต์ — API ทั้งหมดอยู่ใต้ /api/ ตามที่ frontend proxy ไว้"""

from django.contrib import admin
from django.urls import path

from common.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
]
