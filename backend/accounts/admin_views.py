from rest_framework.generics import ListAPIView, RetrieveAPIView

from common.pagination import StandardPagination

from .admin_serializers import (
    AdminUserDetailSerializer,
    AdminUserListSerializer,
    AdminUserQuerySerializer,
)
from .admin_users import list_users, role_counts
from .models import User
from .permissions import IsAdminRole


class NoStoreMixin:
    """ห้ามเบราว์เซอร์หรือ proxy เก็บ cache คำตอบ (มีข้อมูลส่วนบุคคลของผู้ใช้) รวมถึงคำตอบที่เป็น error"""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class AdminUserListView(NoStoreMixin, ListAPIView):
    """GET /api/admin/users/ — รายชื่อผู้ใช้ (ค้นหา กรองบทบาท/สถานะ แบ่งหน้า) เฉพาะ Admin

    คำตอบเป็นรูปแบบของ StandardPagination + role_counts (ตัวเลขบนแท็บบทบาท)
    สิทธิ์ตรวจก่อนตรวจพารามิเตอร์: คนที่ไม่ใช่ Admin ไม่เห็นแม้แต่ข้อความ error ของตัวกรอง
    """

    permission_classes = [IsAdminRole]
    serializer_class = AdminUserListSerializer
    pagination_class = StandardPagination

    def list(self, request, *args, **kwargs):
        params = AdminUserQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        role = params.validated_data.get("role")
        status = params.validated_data.get("status")
        search = params.validated_data.get("search", "")

        page = self.paginate_queryset(list_users(role=role, status=status, search=search))
        response = self.get_paginated_response(self.get_serializer(page, many=True).data)
        # ตัวเลขบนแท็บนับตามคำค้นและสถานะ แต่ไม่นับตามบทบาทที่เลือกอยู่
        response.data["role_counts"] = role_counts(status=status, search=search)
        return response


class AdminUserDetailView(NoStoreMixin, RetrieveAPIView):
    """GET /api/admin/users/{id}/ — ข้อมูลผู้ใช้ 1 คนสำหรับหน้าแก้ไข เฉพาะ Admin (ดูบัญชีที่ปิดใช้งานแล้วได้)"""

    permission_classes = [IsAdminRole]
    serializer_class = AdminUserDetailSerializer
    # ดึงผู้สร้างมาพร้อมกันในคิวรีเดียว (ใช้แสดง "สร้างบัญชีโดย ...")
    queryset = User.objects.select_related("created_by")
