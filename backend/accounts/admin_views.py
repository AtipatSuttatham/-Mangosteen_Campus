from rest_framework import status as http_status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import request_context
from common.pagination import StandardPagination

from .admin_serializers import (
    AdminUserDetailSerializer,
    AdminUserListSerializer,
    AdminUserQuerySerializer,
    AdminUserWriteSerializer,
)
from .admin_users import list_users, role_counts
from .models import User
from .permissions import IsAdminRole
from .user_management import (
    Outcome,
    create_user_by_admin,
    resend_invite,
    set_user_active,
    update_user_by_admin,
)


class NoStoreMixin:
    """ห้ามเบราว์เซอร์หรือ proxy เก็บ cache คำตอบ (มีข้อมูลส่วนบุคคลของผู้ใช้) รวมถึงคำตอบที่เป็น error"""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


def _user_response(user: User, *, status: int = http_status.HTTP_200_OK, **extra) -> Response:
    """คำตอบของการเขียนทุกแบบ: {"user": <รายละเอียดผู้ใช้>} + ฟิลด์เสริม (เช่น email_sent)"""
    return Response({"user": AdminUserDetailSerializer(user).data, **extra}, status=status)


def _outcome_response(outcome: Outcome, *, status: int = http_status.HTTP_200_OK) -> Response:
    # email_sent: true/false ตามที่ส่งจริง, null = การกระทำนี้ไม่ต้องส่งอีเมล
    return _user_response(outcome.user, status=status, email_sent=outcome.email_sent)


class AdminUserListView(NoStoreMixin, ListAPIView):
    """/api/admin/users/ — GET รายชื่อผู้ใช้ (ค้นหา กรองบทบาท/สถานะ แบ่งหน้า) / POST สร้างบัญชี เฉพาะ Admin

    GET: คำตอบเป็นรูปแบบของ StandardPagination + role_counts (ตัวเลขบนแท็บบทบาท)
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

    def post(self, request):
        """สร้างบัญชี (ยังไม่มีรหัสผ่าน) แล้วส่งลิงก์ตั้งรหัสผ่านอายุ 7 วัน — 201 + email_sent"""
        serializer = AdminUserWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        outcome = create_user_by_admin(
            actor=request.user,
            audit_context=request_context(request),
            **serializer.validated_data,
        )
        return _outcome_response(outcome, status=http_status.HTTP_201_CREATED)


class AdminUserDetailView(NoStoreMixin, RetrieveAPIView):
    """/api/admin/users/{id}/ — GET ข้อมูลผู้ใช้ 1 คนสำหรับหน้าแก้ไข / PATCH แก้ข้อมูล เฉพาะ Admin

    GET ดูบัญชีที่ปิดใช้งานแล้วได้ด้วย
    """

    permission_classes = [IsAdminRole]
    serializer_class = AdminUserDetailSerializer
    # ดึงผู้สร้างมาพร้อมกันในคิวรีเดียว (ใช้แสดง "สร้างบัญชีโดย ...")
    queryset = User.objects.select_related("created_by")

    def patch(self, request, pk):
        """แก้ข้อมูลบางฟิลด์ (ส่งเฉพาะที่แก้) — 200 + email_sent (null = ไม่ต้องส่งอีเมล)"""
        user = self.get_object()
        serializer = AdminUserWriteSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        outcome = update_user_by_admin(
            actor=request.user,
            user_id=user.pk,
            updates=serializer.validated_data,
            audit_context=request_context(request),
        )
        return _outcome_response(outcome)


class _AdminUserActionView(NoStoreMixin, APIView):
    """แม่แบบของ endpoint แบบ "กระทำต่อผู้ใช้ 1 คน" (POST ไม่มี body) เฉพาะ Admin"""

    permission_classes = [IsAdminRole]


class AdminUserDeactivateView(_AdminUserActionView):
    """POST /api/admin/users/{id}/deactivate/ — ปิดใช้งานบัญชี (ตัวเอง/Admin คนสุดท้ายไม่ได้ → 409)"""

    def post(self, request, pk):
        user = set_user_active(
            actor=request.user,
            user_id=pk,
            is_active=False,
            audit_context=request_context(request),
        )
        return _user_response(user)


class AdminUserActivateView(_AdminUserActionView):
    """POST /api/admin/users/{id}/activate/ — เปิดใช้งานบัญชีกลับ (ทันที ไม่ต้องยืนยัน)"""

    def post(self, request, pk):
        user = set_user_active(
            actor=request.user,
            user_id=pk,
            is_active=True,
            audit_context=request_context(request),
        )
        return _user_response(user)


class AdminUserResendInviteView(_AdminUserActionView):
    """POST /api/admin/users/{id}/resend-invite/ — ส่งลิงก์ตั้งรหัสผ่านซ้ำ (เฉพาะสถานะรอตั้งรหัสผ่าน)

    ยังไม่พ้น 60 วินาทีจากลิงก์ล่าสุด → 429 พร้อม retry_after / สถานะอื่น → 409
    """

    def post(self, request, pk):
        outcome = resend_invite(
            actor=request.user, user_id=pk, audit_context=request_context(request)
        )
        return _outcome_response(outcome)
