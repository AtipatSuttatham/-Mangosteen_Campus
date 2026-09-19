from django.contrib.auth.models import update_last_login
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .exceptions import InvalidRefreshToken, MissingRequestedWithHeader
from .password_reset import check_reset_token, request_password_reset, reset_password
from .registration import register_student, resend_verification, verify_email
from .serializers import (
    EmailOnlySerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    TokenSerializer,
    UserSerializer,
)
from .services import authenticate_identifier
from .tokens import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    issue_refresh_token,
    load_refresh_token,
    set_refresh_cookie,
)


def _require_requested_with(request) -> None:
    """คำขอที่ใช้ cookie (refresh / logout) ต้องมี header X-Requested-With (เหตุผลดูที่ exceptions.py)"""
    if not request.headers.get("X-Requested-With"):
        raise MissingRequestedWithHeader


def _session_response(refresh: RefreshToken, user) -> Response:
    """ตอบ access token (ให้เว็บเก็บในหน่วยความจำ) + ข้อมูลผู้ใช้ และตั้ง cookie refresh token ใหม่"""
    response = Response({"access": str(refresh.access_token), "user": UserSerializer(user).data})
    set_refresh_cookie(response, refresh)
    # ห้ามให้เบราว์เซอร์หรือ proxy เก็บ cache คำตอบที่มี token
    response["Cache-Control"] = "no-store"
    return response


class LoginView(APIView):
    """POST /api/auth/login/ — เข้าสู่ระบบด้วยรหัสนักศึกษา/พนักงานหรืออีเมล + รหัสผ่าน"""

    # เปิดให้ทุกคนเรียกได้ และไม่ตรวจ token เดิม (token หมดอายุที่แนบมาจะได้ไม่ทำให้ login พัง)
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate_identifier(**serializer.validated_data)
        # บันทึกเวลาเข้าสู่ระบบล่าสุด
        update_last_login(None, user)
        return _session_response(issue_refresh_token(user), user)


class RefreshView(APIView):
    """POST /api/auth/refresh/ — แลก refresh token (จาก cookie) เป็น access token ใหม่

    พร้อมหมุนเวียน: เพิกถอนใบเดิมแล้วตั้ง cookie ใบใหม่
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        _require_requested_with(request)

        try:
            raw_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
            if not raw_token:
                raise InvalidRefreshToken
            old_token, user = load_refresh_token(raw_token)
        except InvalidRefreshToken as exc:
            # cookie ใช้ไม่ได้แล้ว: ตอบ 401 และสั่งลบ cookie ทิ้ง
            response = Response(
                {"code": exc.default_code, "detail": str(exc.detail)}, status=exc.status_code
            )
            clear_refresh_cookie(response)
            return response

        # เพิกถอนใบเก่า (ใช้ซ้ำไม่ได้) แล้วออกใบใหม่จากข้อมูลผู้ใช้ปัจจุบัน
        # role ที่ Admin เพิ่งเปลี่ยนจึงมีผลกับ token ชุดใหม่ทันที
        old_token.blacklist()
        return _session_response(issue_refresh_token(user), user)


class LogoutView(APIView):
    """POST /api/auth/logout/ — เพิกถอน refresh token และลบ cookie (เรียกซ้ำกี่ครั้งก็ได้ผลเหมือนเดิม)"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        _require_requested_with(request)

        raw_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()
            except TokenError:
                # token ใช้ไม่ได้อยู่แล้ว (หมดอายุ/ถูกเพิกถอนแล้ว) ไม่ต้องทำอะไรเพิ่ม
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response


class RegisterView(APIView):
    """POST /api/auth/register/ — สมัครเองด้วยอีเมล (ได้บัญชีผู้เรียนที่ต้องยืนยันอีเมลก่อนใช้งาน)"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        register_student(**serializer.validated_data)
        # 202 = รับเรื่องแล้ว รออีเมลยืนยัน (ยังไม่ล็อกอินให้ และไม่ส่งข้อมูลบัญชีกลับ)
        return Response({}, status=status.HTTP_202_ACCEPTED)


class VerifyEmailView(APIView):
    """POST /api/auth/verify-email/ — ยืนยันอีเมลด้วยโทเคนจากลิงก์

    ใช้ POST ไม่ใช่ GET: โปรแกรมสแกนลิงก์ของอีเมลหลายเจ้าเปิดลิงก์ล่วงหน้า ถ้าเป็น GET
    ลิงก์จะถูกใช้ไปก่อนที่ผู้ใช้กด หน้าเว็บ /verify-email จึงอ่านโทเคนจากลิงก์แล้วเรียก POST เอง
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verify_email(serializer.validated_data["token"])
        return Response({"email_verified": True})


class ResendVerificationView(APIView):
    """POST /api/auth/resend-verification/ — ขอลิงก์ยืนยันอีเมลใหม่

    ตอบ 202 เหมือนกันทุกกรณี (ไม่มีอีเมลนี้ / ยืนยันแล้ว / ยังไม่พ้น 60 วินาที / ส่งแล้ว)
    เพื่อไม่ให้ใครใช้ endpoint นี้เดาว่าอีเมลไหนมีบัญชี
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resend_verification(serializer.validated_data["email"])
        return Response({}, status=status.HTTP_202_ACCEPTED)


class ForgotPasswordView(APIView):
    """POST /api/auth/forgot-password/ — ขอลิงก์ตั้งรหัสผ่านใหม่ทางอีเมล

    ตอบ 202 เหมือนกันทุกกรณี (ไม่มีอีเมลนี้ / ยังไม่ยืนยันอีเมล / บัญชีถูกปิด / ยังไม่พ้น 60 วินาที / ส่งแล้ว)
    เพื่อไม่ให้ใครใช้ endpoint นี้เดาว่าอีเมลไหนมีบัญชี
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_password_reset(serializer.validated_data["email"])
        return Response({}, status=status.HTTP_202_ACCEPTED)


class ResetPasswordCheckView(APIView):
    """POST /api/auth/reset-password/check/ — ตรวจลิงก์ตั้งรหัสผ่านโดยไม่ใช้โทเคนทิ้ง

    ให้หน้าเว็บ /reset-password ตรวจลิงก์ตั้งแต่เปิดหน้า: แสดงว่าตั้งรหัสให้บัญชีไหน
    หรือบอกทันทีว่าลิงก์หมดอายุ (ไม่ต้องรอให้กรอกรหัสเสร็จแล้วค่อยเจอ)
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = check_reset_token(serializer.validated_data["token"])
        # อีเมลเต็มได้ เพราะผู้ถือโทเคนคือคนที่เปิดกล่องอีเมลนั้นได้อยู่แล้ว
        return Response({"email": user.email})


class ResetPasswordView(APIView):
    """POST /api/auth/reset-password/ — ตั้งรหัสผ่านใหม่ด้วยโทเคนจากลิงก์

    สำเร็จแล้วเซสชันเดิมทั้งหมดของบัญชีนั้นใช้ไม่ได้ และไม่ล็อกอินให้ (หน้าเว็บพาไปหน้า login)
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        reset_password(data["token"], data["password"])
        return Response({})


class MeView(RetrieveAPIView):
    """GET /api/auth/me/ — ข้อมูลผู้ใช้ที่ล็อกอินอยู่ (ต้องส่ง access token ใน header Authorization)"""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
