import re
from datetime import timedelta

import pytest
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditAction, AuditLog

from .models import EmailVerificationToken, User
from .roles import Role
from .tokens import issue_refresh_token

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres); pytest-django ใช้กล่องอีเมลจำลอง (mail.outbox) ให้เอง
pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
NEW_PASSWORD = "Xk9-plum-Harbor-42"  # ผ่านกฎรหัสผ่านของระบบ (ไม่คล้ายชื่อ/อีเมล)
USABLE_HASH = make_password(PASSWORD)
NO_PASSWORD = "!not-set-yet"

LIST_URL = reverse("admin-user-list")

DETAIL_FIELDS = {
    "id",
    "email",
    "student_or_staff_id",
    "role",
    "first_name",
    "last_name",
    "first_name_en",
    "last_name_en",
    "status",
    "is_active",
    "is_email_verified",
    "last_login",
    "date_joined",
    "updated_at",
    "created_by",
}

NEW_USER = {
    "role": "teacher",
    "first_name": "วิภา",
    "last_name": "สุขสวัสดิ์",
    "email": "wipha.s@example.ac.th",
}


@pytest.fixture(autouse=True)
def frontend_url(settings):
    settings.FRONTEND_URL = "https://campus.example.ac.th"


def url(name, user):
    return reverse(f"admin-user-{name}", args=[user.pk])


def bearer(user):
    return f"Bearer {issue_refresh_token(user).access_token}"


def client_for(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=bearer(user))
    return client


def make_user(email, role=Role.STUDENT, **extra):
    fields = {
        "password": USABLE_HASH,
        "first_name": "สมชาย",
        "last_name": "ใจดี",
        "is_email_verified": True,
    }
    fields.update(extra)
    return User.objects.create(email=email, role=role, **fields)


def token_in_last_email():
    return re.search(r"token=([\w-]+)", mail.outbox[-1].body).group(1)


@pytest.fixture
def admin():
    return make_user("admin@example.com", role=Role.ADMIN, first_name="อภิชาติ", last_name="วงศ์สกุล")


@pytest.fixture
def api(admin):
    return client_for(admin)


class TestPermissions:
    """ทุก endpoint เขียน: คนไม่ล็อกอิน 401, ผู้ที่ไม่ใช่ Admin 403 และต้องไม่เกิดผลข้างเคียงใด ๆ"""

    @pytest.fixture
    def target(self):
        return make_user("target@example.com", password=NO_PASSWORD)

    def calls(self, target):
        return [
            ("post", LIST_URL, NEW_USER),
            ("patch", url("detail", target), {"first_name": "แก้"}),
            ("post", url("deactivate", target), None),
            ("post", url("activate", target), None),
            ("post", url("resend-invite", target), None),
        ]

    def test_anonymous_gets_401_everywhere(self, target):
        for method, endpoint, body in self.calls(target):
            response = getattr(APIClient(), method)(endpoint, body, format="json")

            assert response.status_code == 401, endpoint

    @pytest.mark.parametrize("role", [Role.TEACHER, Role.STUDENT])
    def test_other_roles_get_403_and_nothing_happens(self, target, role):
        client = client_for(make_user(f"{role}@example.com", role=role))
        users_before = User.objects.count()

        for method, endpoint, body in self.calls(target):
            response = getattr(client, method)(endpoint, body, format="json")

            assert response.status_code == 403, endpoint
            assert response.data["code"] == "permission_denied"

        target.refresh_from_db()
        assert (target.first_name, target.is_active) == ("สมชาย", True)
        assert User.objects.count() == users_before
        assert AuditLog.objects.count() == 0
        assert mail.outbox == []


class TestCreate:
    def post(self, api, **overrides):
        return api.post(LIST_URL, {**NEW_USER, **overrides}, format="json")

    def test_creates_the_account_and_answers_201(self, api, admin):
        response = self.post(api, student_or_staff_id="T0057", first_name_en="Wipha")

        assert response.status_code == 201
        assert set(response.data) == {"user", "email_sent"}
        assert response.data["email_sent"] is True
        assert set(response.data["user"]) == DETAIL_FIELDS
        assert response.data["user"]["status"] == "pending_password"
        assert response.data["user"]["created_by"] == {"id": admin.pk, "full_name": "อภิชาติ วงศ์สกุล"}
        user = User.objects.get(email="wipha.s@example.ac.th")
        assert (user.role, user.student_or_staff_id, user.first_name_en) == (
            "teacher",
            "T0057",
            "Wipha",
        )
        assert user.is_email_verified is True
        assert user.has_usable_password() is False
        assert response["Cache-Control"] == "no-store"

    def test_the_link_in_the_email_completes_the_whole_journey(self, api):
        """สร้างบัญชี → กดลิงก์ในอีเมล → ตั้งรหัสผ่าน → เข้าสู่ระบบได้จริง (วงจรครบทั้งเส้น)"""
        self.post(api)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["wipha.s@example.ac.th"]
        anonymous = APIClient()

        # ก่อนตั้งรหัสผ่านเข้าสู่ระบบไม่ได้
        before = anonymous.post(
            reverse("auth-login"),
            {"identifier": "wipha.s@example.ac.th", "password": NEW_PASSWORD},
            format="json",
        )
        assert before.status_code == 401

        # หน้าเว็บตรวจลิงก์แล้วตั้งรหัสผ่าน
        token = token_in_last_email()
        checked = anonymous.post(reverse("auth-reset-check"), {"token": token}, format="json")
        assert checked.data == {"email": "wipha.s@example.ac.th"}
        done = anonymous.post(
            reverse("auth-reset-password"),
            {"token": token, "password": NEW_PASSWORD},
            format="json",
        )
        assert done.status_code == 200

        # เข้าสู่ระบบได้ ได้บทบาทผู้สอน แต่เรียก API ของ Admin ไม่ได้
        login = anonymous.post(
            reverse("auth-login"),
            {"identifier": "wipha.s@example.ac.th", "password": NEW_PASSWORD},
            format="json",
        )
        assert login.status_code == 200
        assert login.data["user"]["role"] == "teacher"
        teacher = APIClient()
        teacher.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        assert teacher.get(LIST_URL).status_code == 403

        # ลิงก์ใช้ได้ครั้งเดียว และสถานะในรายชื่อของ Admin กลายเป็นใช้งานอยู่
        again = anonymous.post(
            reverse("auth-reset-password"),
            {"token": token, "password": NEW_PASSWORD},
            format="json",
        )
        assert again.status_code == 400
        created = User.objects.get(email="wipha.s@example.ac.th")
        assert api.get(url("detail", created)).data["status"] == "active"

    def test_creating_an_admin_does_not_grant_django_admin_rights(self, api):
        response = self.post(api, role="admin")

        assert response.status_code == 201
        user = User.objects.get(email=NEW_USER["email"])
        assert (user.role, user.is_staff, user.is_superuser) == ("admin", False, False)

    def test_extra_fields_cannot_set_privileges_or_password(self, api, admin):
        # กัน mass assignment: ฟิลด์ที่ไม่ได้ประกาศไว้ต้องถูกทิ้งทั้งหมด
        other = make_user("other@example.com")

        response = self.post(
            api,
            password="hacked-Passw0rd!",
            is_active=False,
            is_staff=True,
            is_superuser=True,
            is_email_verified=False,
            created_by=other.pk,
            id=999,
            date_joined="2000-01-01T00:00:00Z",
            last_login="2000-01-01T00:00:00Z",
        )

        assert response.status_code == 201
        user = User.objects.get(email=NEW_USER["email"])
        assert user.has_usable_password() is False
        assert (user.is_active, user.is_staff, user.is_superuser) == (True, False, False)
        assert user.is_email_verified is True
        assert user.created_by == admin
        assert user.pk != 999
        assert user.date_joined.year >= 2026
        assert user.last_login is None

    def test_writes_one_audit_entry_with_request_context(self, api, admin):
        response = self.post(api)

        (row,) = AuditLog.objects.all()
        assert row.action == AuditAction.CREATE
        assert row.actor == admin
        assert row.object_id == str(response.data["user"]["id"])
        assert row.context["path"] == "/api/admin/users/"
        assert row.context["ip"] == "127.0.0.1"
        assert row.changes["role"] == [None, "teacher"]
        assert "password" not in str(row.changes).lower()

    def test_email_failure_still_answers_201_with_email_sent_false(self, api, monkeypatch):
        def boom(user, raw_token):
            raise RuntimeError("smtp down")

        monkeypatch.setattr("accounts.user_management.send_account_invite_email", boom)

        response = self.post(api)

        assert response.status_code == 201
        assert response.data["email_sent"] is False
        assert User.objects.filter(email=NEW_USER["email"]).exists()

    def test_blank_optional_fields_are_stored_as_no_value(self, api):
        response = self.post(api, student_or_staff_id="", first_name_en="", last_name_en="")

        assert response.status_code == 201
        user = User.objects.get(email=NEW_USER["email"])
        assert user.student_or_staff_id is None
        assert (user.first_name_en, user.last_name_en) == ("", "")

    def test_names_and_email_are_trimmed_and_the_email_lowercased(self, api):
        response = self.post(api, first_name="  วิภา ", email="  Wipha.S@Example.AC.th ")

        assert response.status_code == 201
        user = User.objects.get(email="wipha.s@example.ac.th")
        assert user.first_name == "วิภา"

    @pytest.mark.parametrize("missing", ["role", "first_name", "last_name", "email"])
    def test_required_fields(self, api, missing):
        body = {key: value for key, value in NEW_USER.items() if key != missing}

        response = api.post(LIST_URL, body, format="json")

        assert response.status_code == 400
        assert response.data["error_codes"][missing] == ["required"]

    @pytest.mark.parametrize(
        ("field", "value", "code"),
        [
            ("role", "superuser", "invalid_choice"),
            ("email", "not-an-email", "invalid"),
            ("first_name", "   ", "blank"),
            ("first_name", "ก" * 151, "max_length"),
            ("student_or_staff_id", "ก" * 51, "max_length"),
            ("student_or_staff_id", "T0042@x", "staff_id_contains_at_sign"),
        ],
    )
    def test_invalid_values(self, api, field, value, code):
        response = self.post(api, **{field: value})

        assert response.status_code == 400
        assert response.data["code"] == "validation_error"
        assert response.data["error_codes"][field] == [code]

    def test_duplicate_email_ignores_case_and_creates_nothing(self, api):
        make_user("Wipha.S@Example.ac.th".lower())

        response = self.post(api, email="WIPHA.S@example.ac.th")

        assert response.status_code == 400
        assert response.data["error_codes"]["email"] == ["email_taken"]
        assert User.objects.count() == 2  # admin + คนเดิม
        assert AuditLog.objects.count() == 0
        assert mail.outbox == []

    def test_duplicate_staff_id_is_rejected(self, api):
        make_user("other@example.com", student_or_staff_id="T0057")

        response = self.post(api, student_or_staff_id="T0057")

        assert response.status_code == 400
        assert response.data["error_codes"]["student_or_staff_id"] == ["staff_id_taken"]

    def test_every_problem_is_reported_in_one_round(self, api):
        make_user("wipha.s@example.ac.th", student_or_staff_id="T0057")

        response = api.post(
            LIST_URL,
            {
                "role": "teacher",
                "last_name": "x",
                "email": NEW_USER["email"],
                "student_or_staff_id": "T0057",
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error_codes"] == {
            "first_name": ["required"],
            "email": ["email_taken"],
            "student_or_staff_id": ["staff_id_taken"],
        }

    def test_an_email_held_by_an_unverified_self_registration_counts_as_taken(self, api):
        make_user(NEW_USER["email"], is_email_verified=False)

        response = self.post(api)

        assert response.status_code == 400
        assert response.data["error_codes"]["email"] == ["email_taken"]


class TestUpdate:
    def patch(self, api, user, **body):
        return api.patch(url("detail", user), body, format="json")

    def test_changes_fields_and_answers_the_envelope(self, api, admin):
        user = make_user("user@example.com")

        response = self.patch(
            api, user, first_name="สมหมาย", role="teacher", student_or_staff_id="T0009"
        )

        assert response.status_code == 200
        assert set(response.data) == {"user", "email_sent"}
        assert response.data["email_sent"] is None
        assert response.data["user"]["first_name"] == "สมหมาย"
        assert response.data["user"]["role"] == "teacher"
        assert set(response.data["user"]) == DETAIL_FIELDS
        user.refresh_from_db()
        assert (user.first_name, user.role, user.student_or_staff_id) == (
            "สมหมาย",
            "teacher",
            "T0009",
        )
        (row,) = AuditLog.objects.all()
        assert row.action == AuditAction.UPDATE
        assert row.actor == admin
        assert row.context["path"] == f"/api/admin/users/{user.pk}/"
        assert set(row.changes) == {"first_name", "role", "student_or_staff_id"}
        assert response["Cache-Control"] == "no-store"

    def test_empty_body_changes_nothing_and_writes_no_log(self, api):
        user = make_user("user@example.com")

        response = self.patch(api, user)

        assert response.status_code == 200
        assert AuditLog.objects.count() == 0

    def test_password_and_privileges_cannot_be_changed_here(self, api):
        user = make_user("user@example.com")

        response = self.patch(
            api,
            user,
            password="hacked-Passw0rd!",
            is_active=False,
            is_staff=True,
            is_superuser=True,
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.password == USABLE_HASH
        assert (user.is_active, user.is_staff, user.is_superuser) == (True, False, False)
        assert AuditLog.objects.count() == 0

    def test_staff_id_can_be_cleared(self, api):
        user = make_user("user@example.com", student_or_staff_id="T0001")

        response = self.patch(api, user, student_or_staff_id="")

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.student_or_staff_id is None

    def test_keeping_your_own_email_and_staff_id_is_not_a_clash(self, api):
        user = make_user("user@example.com", student_or_staff_id="T0001")

        response = self.patch(
            api, user, email="USER@example.com", student_or_staff_id="T0001", first_name="ใหม่"
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        ("body", "field", "code"),
        [
            ({"role": "boss"}, "role", "invalid_choice"),
            ({"email": "nope"}, "email", "invalid"),
            ({"first_name": " "}, "first_name", "blank"),
            ({"student_or_staff_id": "a@b"}, "student_or_staff_id", "staff_id_contains_at_sign"),
        ],
    )
    def test_invalid_values_are_400_and_change_nothing(self, api, body, field, code):
        user = make_user("user@example.com")

        response = self.patch(api, user, **body)

        assert response.status_code == 400
        assert response.data["error_codes"][field] == [code]
        assert AuditLog.objects.count() == 0

    def test_taken_email_and_staff_id_are_field_errors(self, api):
        make_user("taken@example.com", student_or_staff_id="T0042")
        user = make_user("user@example.com")

        response = self.patch(api, user, email="Taken@example.com", student_or_staff_id="T0042")

        assert response.status_code == 400
        assert response.data["error_codes"] == {
            "email": ["email_taken"],
            "student_or_staff_id": ["staff_id_taken"],
        }

    def test_cannot_change_own_role(self, api, admin):
        response = self.patch(api, admin, role="teacher")

        assert response.status_code == 409
        assert response.data["code"] == "cannot_demote_self"
        admin.refresh_from_db()
        assert admin.role == Role.ADMIN

    def test_role_changes_take_effect_immediately_for_old_tokens(self, api, admin):
        teacher = make_user("teacher@example.com", role=Role.TEACHER)
        teacher_client = client_for(teacher)  # token ออกตอนยังเป็นผู้สอน
        assert teacher_client.get(LIST_URL).status_code == 403

        self.patch(api, teacher, role="admin")
        assert teacher_client.get(LIST_URL).status_code == 200  # ตามฐานข้อมูล ไม่ใช่ role ใน token

        # กลับด้าน: Admin ที่ถูกลดบทบาทใช้ token เดิมไม่ได้ทันที
        self.patch(api, teacher, role="student")
        assert teacher_client.get(LIST_URL).status_code == 403

    def test_changing_the_email_of_a_pending_account_sends_the_new_link_there(self, api):
        user = make_user("old@example.com", password=NO_PASSWORD)

        response = self.patch(api, user, email="New@Example.com")

        assert response.status_code == 200
        assert response.data["email_sent"] is True
        assert response.data["user"]["email"] == "new@example.com"
        assert [m.to for m in mail.outbox] == [["new@example.com"]]
        (row,) = AuditLog.objects.all()
        assert row.changes == {"email": ["old@example.com", "new@example.com"]}

    def test_changing_the_email_of_an_active_account_keeps_it_verified_and_sends_nothing(self, api):
        user = make_user("old@example.com")

        response = self.patch(api, user, email="new@example.com")

        assert response.data["email_sent"] is None
        assert response.data["user"]["is_email_verified"] is True
        assert mail.outbox == []

    def test_unknown_user_is_404(self, api):
        response = api.patch(
            reverse("admin-user-detail", args=[999999]), {"first_name": "x"}, format="json"
        )

        assert response.status_code == 404
        assert response.data["code"] == "not_found"

    def test_put_is_not_allowed(self, api):
        user = make_user("user@example.com")

        assert api.put(url("detail", user), NEW_USER, format="json").status_code == 405


class TestActivation:
    def test_deactivating_locks_the_user_out_immediately(self):
        admin = make_user("admin@example.com", role=Role.ADMIN)
        user = User.objects.create_user(
            email="user@example.com", password=PASSWORD, first_name="สมชาย", last_name="ใจดี"
        )
        User.objects.filter(pk=user.pk).update(is_email_verified=True)
        anonymous = APIClient()
        login = anonymous.post(
            reverse("auth-login"),
            {"identifier": "user@example.com", "password": PASSWORD},
            format="json",
        )
        assert login.status_code == 200
        access = login.data["access"]

        response = client_for(admin).post(url("deactivate", user))

        assert response.status_code == 200
        assert response.data["user"]["status"] == "disabled"
        assert response.data["user"]["is_active"] is False
        assert set(response.data) == {"user"}
        # token ที่ยังไม่หมดอายุใช้ไม่ได้ทันที
        me = APIClient()
        me.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert me.get(reverse("auth-me")).status_code == 401
        # เข้าสู่ระบบใหม่ไม่ได้ (ข้อความเดียวกับรหัสผิด ไม่บอกว่าถูกปิด)
        again = anonymous.post(
            reverse("auth-login"),
            {"identifier": "user@example.com", "password": PASSWORD},
            format="json",
        )
        assert again.status_code == 401
        assert again.data["code"] == "invalid_credentials"
        # ต่ออายุเซสชันด้วย cookie เดิมไม่ได้
        refresh = anonymous.post(reverse("auth-refresh"), HTTP_X_REQUESTED_WITH="fetch")
        assert refresh.status_code == 401

    def test_deactivate_and_activate_are_logged_and_reversible(self, api, admin):
        user = make_user("user@example.com", password=NO_PASSWORD)

        off = api.post(url("deactivate", user))
        on = api.post(url("activate", user))

        assert off.data["user"]["status"] == "disabled"
        # เปิดกลับแล้วกลับเป็นสถานะเดิม (ยังรอตั้งรหัสผ่าน) ไม่ใช่ "ใช้งานอยู่"
        assert on.data["user"]["status"] == "pending_password"
        assert [row.changes for row in AuditLog.objects.order_by("id")] == [
            {"is_active": [True, False]},
            {"is_active": [False, True]},
        ]
        assert AuditLog.objects.first().actor == admin

    def test_repeating_is_200_and_logged_once(self, api):
        user = make_user("user@example.com")

        assert api.post(url("deactivate", user)).status_code == 200
        assert api.post(url("deactivate", user)).status_code == 200
        assert AuditLog.objects.count() == 1

    def test_cannot_deactivate_self(self, api, admin):
        response = api.post(url("deactivate", admin))

        assert response.status_code == 409
        assert response.data["code"] == "cannot_deactivate_self"
        admin.refresh_from_db()
        assert admin.is_active is True

    def test_can_deactivate_another_admin(self, api):
        other = make_user("other-admin@example.com", role=Role.ADMIN)

        assert api.post(url("deactivate", other)).status_code == 200

    def test_unknown_user_is_404_and_get_is_not_allowed(self, api):
        user = make_user("user@example.com")

        assert api.post(reverse("admin-user-deactivate", args=[999999])).status_code == 404
        assert api.post(reverse("admin-user-activate", args=[999999])).status_code == 404
        assert api.get(url("deactivate", user)).status_code == 405


class TestResendInvite:
    def create_pending(self, api):
        api.post(LIST_URL, NEW_USER, format="json")
        return User.objects.get(email=NEW_USER["email"])

    def test_immediately_after_creating_is_refused_with_the_wait_time(self, api):
        user = self.create_pending(api)

        response = api.post(url("resend-invite", user))

        assert response.status_code == 429
        assert response.data["code"] == "resend_too_soon"
        assert 1 <= response.data["retry_after"] <= 60
        assert response["Retry-After"] == str(response.data["retry_after"])
        assert len(mail.outbox) == 1  # ไม่ส่งซ้ำ

    def test_after_the_cooldown_it_sends_a_new_link_and_kills_the_old_one(self, api):
        user = self.create_pending(api)
        first_token = token_in_last_email()
        EmailVerificationToken.objects.filter(user=user).update(
            created_at=timezone.now() - timedelta(seconds=61)
        )

        response = api.post(url("resend-invite", user))

        assert response.status_code == 200
        assert response.data["email_sent"] is True
        assert response.data["user"]["status"] == "pending_password"
        assert len(mail.outbox) == 2
        anonymous = APIClient()
        old = anonymous.post(reverse("auth-reset-check"), {"token": first_token}, format="json")
        new = anonymous.post(
            reverse("auth-reset-check"), {"token": token_in_last_email()}, format="json"
        )
        assert old.status_code == 400
        assert new.status_code == 200
        resend_log = AuditLog.objects.order_by("id").last()
        assert resend_log.action == AuditAction.UPDATE
        assert resend_log.changes is None
        assert resend_log.context["event"] == "resend_invite"
        assert resend_log.context["path"] == f"/api/admin/users/{user.pk}/resend-invite/"

    def test_only_pending_accounts_can_be_resent_to(self, api):
        active = make_user("active@example.com")

        response = api.post(url("resend-invite", active))

        assert response.status_code == 409
        assert response.data["code"] == "invite_not_applicable"
        assert mail.outbox == []

    def test_unknown_user_is_404_and_get_is_not_allowed(self, api):
        user = make_user("user@example.com", password=NO_PASSWORD)

        assert api.post(reverse("admin-user-resend-invite", args=[999999])).status_code == 404
        assert api.get(url("resend-invite", user)).status_code == 405
