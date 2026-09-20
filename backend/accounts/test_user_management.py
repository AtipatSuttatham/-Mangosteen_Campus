import re
from datetime import timedelta

import pytest
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from audit.models import AuditAction, AuditLog

from .email_tokens import (
    INVITE_LIFETIME,
    RESET_PASSWORD_LIFETIME,
    VERIFY_EMAIL_LIFETIME,
    issue_token,
    peek_token,
)
from .exceptions import (
    CannotDeactivateSelf,
    CannotDemoteSelf,
    InviteNotApplicable,
    LastAdmin,
    ResendTooSoon,
    TokenInvalid,
)
from .models import EmailVerificationToken, TokenPurpose, User
from .password_reset import check_reset_token
from .roles import Role
from .user_management import (
    create_user_by_admin,
    resend_invite,
    set_user_active,
    update_user_by_admin,
)
from .user_status import UserStatus, status_of

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres); pytest-django ใช้กล่องอีเมลจำลอง (mail.outbox) ให้เอง
pytestmark = pytest.mark.django_db

RESET = TokenPurpose.RESET_PASSWORD
VERIFY = TokenPurpose.VERIFY_EMAIL
USABLE_HASH = make_password("Str0ng-pass-123")
NO_PASSWORD = "!not-set-yet"  # บัญชีที่ Admin สร้างให้แต่เจ้าของยังไม่ตั้งรหัส


@pytest.fixture(autouse=True)
def frontend_url(settings):
    settings.FRONTEND_URL = "https://campus.example.ac.th"


def make_user(email, role=Role.STUDENT, **extra):
    """ผู้ใช้ที่ใช้งานอยู่ ยืนยันอีเมลแล้ว (ปรับเปลี่ยนได้ผ่าน extra)"""
    fields = {
        "password": USABLE_HASH,
        "first_name": "สมชาย",
        "last_name": "ใจดี",
        "is_email_verified": True,
    }
    fields.update(extra)
    return User.objects.create(email=email, role=role, **fields)


@pytest.fixture
def admin():
    return make_user("admin@example.com", role=Role.ADMIN)


def token_in_last_email():
    """ดึงโทเคนจากลิงก์ในอีเมลฉบับล่าสุดที่ส่งออก"""
    return re.search(r"token=([\w-]+)", mail.outbox[-1].body).group(1)


def audit_rows():
    return list(AuditLog.objects.order_by("id"))


class TestCreate:
    def create(self, admin, **overrides):
        data = {
            "actor": admin,
            "role": Role.TEACHER,
            "email": "New@Example.com",
            "first_name": "วิภา",
            "last_name": "สุขสวัสดิ์",
        }
        data.update(overrides)
        return create_user_by_admin(**data)

    def test_creates_a_verified_account_without_a_password(self, admin):
        outcome = self.create(admin)

        user = User.objects.get(email="new@example.com")
        assert outcome.user == user
        assert user.role == Role.TEACHER
        assert user.created_by == admin
        assert user.is_email_verified is True
        assert user.is_active is True
        assert user.has_usable_password() is False
        assert status_of(user) == UserStatus.PENDING_PASSWORD

    def test_never_gets_django_admin_rights_even_when_role_is_admin(self, admin):
        outcome = self.create(admin, role=Role.ADMIN)

        assert outcome.user.role == Role.ADMIN
        assert outcome.user.is_staff is False
        assert outcome.user.is_superuser is False

    def test_sends_one_invite_to_the_new_address_with_a_seven_day_link(self, admin):
        before = timezone.now()

        outcome = self.create(admin)

        assert outcome.email_sent is True
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["new@example.com"]
        assert "/reset-password?token=" in mail.outbox[0].body
        assert "7 วัน" in mail.outbox[0].body
        stored = EmailVerificationToken.objects.get()
        assert stored.purpose == RESET
        assert stored.expires_at >= before + INVITE_LIFETIME
        assert peek_token(token_in_last_email(), RESET) == outcome.user

    def test_records_one_create_entry_without_secrets(self, admin):
        outcome = self.create(admin, audit_context={"ip": "10.0.0.5", "path": "/api/admin/users/"})

        (row,) = audit_rows()
        assert row.action == AuditAction.CREATE
        assert row.actor == admin
        assert row.object_id == str(outcome.user.pk)
        assert row.changes["email"] == [None, "new@example.com"]
        assert row.changes["role"] == [None, "teacher"]
        assert row.changes["is_active"] == [None, True]
        assert row.context == {"ip": "10.0.0.5", "path": "/api/admin/users/"}
        stored = str(row.changes) + str(row.context) + row.object_repr
        assert "password" not in stored.lower()
        assert token_in_last_email() not in stored

    def test_blank_optional_fields_are_not_logged_as_changes(self, admin):
        self.create(admin)

        (row,) = audit_rows()
        assert "first_name_en" not in row.changes
        assert "student_or_staff_id" not in row.changes

    def test_email_failure_still_creates_the_account(self, admin, monkeypatch):
        def boom(user, raw_token):
            raise RuntimeError("smtp down")

        monkeypatch.setattr("accounts.user_management.send_account_invite_email", boom)

        outcome = self.create(admin)

        assert outcome.email_sent is False
        assert User.objects.filter(email="new@example.com").exists()
        # ลิงก์ถูกออกไว้แล้ว (Admin กด "ส่งลิงก์อีกครั้ง" ได้ เมื่อพ้นกฎรอ 60 วินาที)
        assert EmailVerificationToken.objects.filter(user=outcome.user, used_at=None).count() == 1

    def test_failure_to_write_the_log_rolls_everything_back_and_sends_nothing(
        self, admin, monkeypatch
    ):
        def boom(**kwargs):
            raise RuntimeError("audit down")

        monkeypatch.setattr("accounts.user_management.log_action", boom)

        with pytest.raises(RuntimeError):
            self.create(admin)

        assert not User.objects.filter(email="new@example.com").exists()
        assert EmailVerificationToken.objects.count() == 0
        assert mail.outbox == []

    def test_taken_email_is_a_field_error_even_when_the_race_is_lost_at_the_database(self, admin):
        # เรียก service ตรง ๆ (ข้ามการตรวจซ้ำของ serializer) จำลองสองคำขอที่แข่งกันจนชน unique จริง
        make_user("new@example.com")

        with pytest.raises(ValidationError) as caught:
            self.create(admin)

        assert caught.value.detail["email"][0].code == "email_taken"
        # ธุรกรรมหลักยังใช้งานต่อได้ และไม่มีอะไรหลงเหลือ
        assert User.objects.filter(email="new@example.com").count() == 1
        assert audit_rows() == []
        assert mail.outbox == []

    def test_taken_staff_id_is_a_field_error(self, admin):
        make_user("other@example.com", student_or_staff_id="T0042")

        with pytest.raises(ValidationError) as caught:
            self.create(admin, student_or_staff_id="T0042")

        assert caught.value.detail["student_or_staff_id"][0].code == "staff_id_taken"
        assert set(caught.value.detail) == {"student_or_staff_id"}

    def test_both_taken_are_reported_together(self, admin):
        make_user("new@example.com", student_or_staff_id="T0042")

        with pytest.raises(ValidationError) as caught:
            self.create(admin, student_or_staff_id="T0042")

        assert set(caught.value.detail) == {"email", "student_or_staff_id"}

    def test_two_accounts_without_a_staff_id_do_not_clash(self, admin):
        # รหัสว่างต้องเก็บเป็น NULL ไม่ใช่สตริงว่าง ไม่งั้นคนที่ไม่มีรหัสชน unique กัน
        self.create(admin, email="a@example.com", student_or_staff_id="")
        self.create(admin, email="b@example.com", student_or_staff_id=None)

        assert User.objects.filter(student_or_staff_id__isnull=True).count() == 3  # รวม admin


class TestUpdate:
    def update(self, admin, user, **updates):
        return update_user_by_admin(actor=admin, user_id=user.pk, updates=updates)

    def test_nothing_changed_writes_nothing(self, admin):
        user = make_user("user@example.com")
        updated_at = User.objects.get(pk=user.pk).updated_at

        outcome = self.update(admin, user, role=Role.STUDENT, first_name="สมชาย")

        assert outcome.email_sent is None
        assert audit_rows() == []
        assert mail.outbox == []
        assert User.objects.get(pk=user.pk).updated_at == updated_at

    def test_changes_only_the_given_fields_and_logs_only_what_changed(self, admin):
        user = make_user("user@example.com", first_name_en="Somchai")

        self.update(admin, user, first_name="สมหมาย", role=Role.TEACHER, last_name="ใจดี")

        user.refresh_from_db()
        assert (user.first_name, user.last_name, user.role) == ("สมหมาย", "ใจดี", Role.TEACHER)
        assert user.first_name_en == "Somchai"  # ไม่ได้ส่งมา จึงไม่ถูกแตะ
        (row,) = audit_rows()
        assert row.action == AuditAction.UPDATE
        assert row.actor == admin
        assert row.changes == {"first_name": ["สมชาย", "สมหมาย"], "role": ["student", "teacher"]}

    def test_updated_at_moves_when_something_changes(self, admin):
        user = make_user("user@example.com")
        old = User.objects.get(pk=user.pk).updated_at

        self.update(admin, user, first_name="ใหม่")

        assert User.objects.get(pk=user.pk).updated_at > old

    def test_keys_outside_the_profile_fields_are_ignored(self, admin):
        user = make_user("user@example.com")

        self.update(
            admin, user, first_name="ใหม่", is_active=False, password="hacked!", is_staff=True
        )

        user.refresh_from_db()
        assert user.first_name == "ใหม่"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.password == USABLE_HASH

    def test_unknown_user_is_404(self, admin):
        with pytest.raises(Http404):
            update_user_by_admin(actor=admin, user_id=999999, updates={"first_name": "x"})

    def test_staff_id_can_be_set_changed_and_cleared(self, admin):
        user = make_user("user@example.com")

        self.update(admin, user, student_or_staff_id="  T0042 ")
        user.refresh_from_db()
        assert user.student_or_staff_id == "T0042"

        self.update(admin, user, student_or_staff_id=None)
        user.refresh_from_db()
        assert user.student_or_staff_id is None
        assert audit_rows()[-1].changes == {"student_or_staff_id": ["T0042", None]}

    def test_taken_staff_id_is_a_field_error_and_changes_nothing(self, admin):
        make_user("other@example.com", student_or_staff_id="T0042")
        user = make_user("user@example.com", student_or_staff_id="T0001")

        with pytest.raises(ValidationError) as caught:
            self.update(admin, user, student_or_staff_id="T0042", first_name="ใหม่")

        assert caught.value.detail["student_or_staff_id"][0].code == "staff_id_taken"
        user.refresh_from_db()
        assert (user.student_or_staff_id, user.first_name) == ("T0001", "สมชาย")
        assert audit_rows() == []

    class TestRoleRules:
        def test_cannot_change_own_role(self, admin):
            with pytest.raises(CannotDemoteSelf):
                update_user_by_admin(actor=admin, user_id=admin.pk, updates={"role": Role.TEACHER})

            admin.refresh_from_db()
            assert admin.role == Role.ADMIN
            assert audit_rows() == []

        def test_own_profile_and_email_can_be_edited(self, admin):
            outcome = update_user_by_admin(
                actor=admin,
                user_id=admin.pk,
                updates={"first_name": "ใหม่", "role": Role.ADMIN, "email": "root@example.com"},
            )

            admin.refresh_from_db()
            assert (admin.first_name, admin.email, admin.role) == (
                "ใหม่",
                "root@example.com",
                "admin",
            )
            assert outcome.email_sent is None  # บัญชีใช้งานอยู่ ไม่ส่งอะไร

        def test_can_demote_another_admin_while_one_remains(self, admin):
            other = make_user("other-admin@example.com", role=Role.ADMIN)

            update_user_by_admin(actor=admin, user_id=other.pk, updates={"role": Role.TEACHER})

            other.refresh_from_db()
            assert other.role == Role.TEACHER

        def test_cannot_remove_the_last_active_admin(self, admin):
            # ผู้กระทำ (admin) ถูกลดบทบาทในฐานข้อมูลระหว่างที่คำขอยังถือ token เดิม (ช่องโหว่ที่ต้องกัน:
            # Admin สองคนลดกันเองพร้อมกัน) เหลือ Admin ที่ใช้งานอยู่แค่คนเดียว = เป้าหมาย
            target = make_user("target-admin@example.com", role=Role.ADMIN)
            User.objects.filter(pk=admin.pk).update(role=Role.TEACHER)

            with pytest.raises(LastAdmin):
                update_user_by_admin(actor=admin, user_id=target.pk, updates={"role": Role.STUDENT})

            target.refresh_from_db()
            assert target.role == Role.ADMIN
            assert audit_rows() == []

        def test_demoting_an_inactive_admin_is_allowed(self, admin):
            # Admin ที่ปิดใช้งานอยู่ไม่นับเป็น "Admin ที่ใช้งานอยู่" การลดบทบาทจึงไม่ทำให้เหลือน้อยลง
            inactive = make_user("old-admin@example.com", role=Role.ADMIN, is_active=False)
            User.objects.filter(pk=admin.pk).update(role=Role.TEACHER)

            update_user_by_admin(actor=admin, user_id=inactive.pk, updates={"role": Role.STUDENT})

            inactive.refresh_from_db()
            assert inactive.role == Role.STUDENT

        def test_promoting_someone_never_hits_the_rules(self, admin):
            student = make_user("student@example.com")

            update_user_by_admin(actor=admin, user_id=student.pk, updates={"role": Role.ADMIN})

            student.refresh_from_db()
            assert student.role == Role.ADMIN


class TestChangeEmail:
    """เปลี่ยนอีเมล: โทเคนเก่าต้องตายทุกกรณี และลิงก์ใหม่ไป "อีเมลใหม่" ตามสถานะ"""

    NEW = "changed@example.com"

    def change(self, admin, user):
        return update_user_by_admin(actor=admin, user_id=user.pk, updates={"email": self.NEW})

    def test_pending_password_gets_a_new_invite_at_the_new_address(self, admin):
        user = make_user("old@example.com", password=NO_PASSWORD)
        old_token = issue_token(user, RESET, INVITE_LIFETIME)

        outcome = self.change(admin, user)

        assert outcome.email_sent is True
        assert [m.to for m in mail.outbox] == [[self.NEW]]  # ไม่ส่งไปอีเมลเดิม
        assert "/reset-password?token=" in mail.outbox[0].body
        assert "7 วัน" in mail.outbox[0].body
        with pytest.raises(TokenInvalid):
            peek_token(old_token, RESET)
        assert peek_token(token_in_last_email(), RESET).email == self.NEW

    def test_pending_verification_gets_a_new_verification_link_and_stays_unverified(self, admin):
        user = make_user("old@example.com", is_email_verified=False)
        old_token = issue_token(user, VERIFY, VERIFY_EMAIL_LIFETIME)

        outcome = self.change(admin, user)

        assert outcome.email_sent is True
        assert mail.outbox[0].to == [self.NEW]
        assert "/verify-email?token=" in mail.outbox[0].body
        with pytest.raises(TokenInvalid):
            peek_token(old_token, VERIFY)
        assert peek_token(token_in_last_email(), VERIFY).is_email_verified is False

    def test_active_account_keeps_verified_status_and_gets_no_email(self, admin):
        user = make_user("old@example.com")
        # ลิงก์ "ลืมรหัสผ่าน" ที่ผู้ใช้ขอไว้ก่อนหน้า (ส่งไปอีเมลเดิม) ต้องตายเมื่ออีเมลเปลี่ยน
        pending_reset = issue_token(user, RESET, RESET_PASSWORD_LIFETIME)

        outcome = self.change(admin, user)

        user.refresh_from_db()
        assert user.email == self.NEW
        assert user.is_email_verified is True
        assert outcome.email_sent is None
        assert mail.outbox == []
        with pytest.raises(TokenInvalid):
            check_reset_token(pending_reset)

    def test_disabled_account_gets_no_email_but_old_links_still_die(self, admin):
        user = make_user("old@example.com", password=NO_PASSWORD, is_active=False)
        old_token = issue_token(user, RESET, INVITE_LIFETIME)

        outcome = self.change(admin, user)

        assert outcome.email_sent is None
        assert mail.outbox == []
        with pytest.raises(TokenInvalid):
            peek_token(old_token, RESET)

    def test_is_logged_as_old_to_new(self, admin):
        user = make_user("old@example.com")

        self.change(admin, user)

        (row,) = audit_rows()
        assert row.changes == {"email": ["old@example.com", self.NEW]}

    def test_taken_email_changes_nothing_and_keeps_old_links_alive(self, admin):
        make_user(self.NEW)
        user = make_user("old@example.com", password=NO_PASSWORD)
        old_token = issue_token(user, RESET, INVITE_LIFETIME)

        with pytest.raises(ValidationError) as caught:
            self.change(admin, user)

        assert caught.value.detail["email"][0].code == "email_taken"
        user.refresh_from_db()
        assert user.email == "old@example.com"
        assert peek_token(old_token, RESET) == user  # ธุรกรรมย้อนกลับ ลิงก์เดิมยังไม่ถูกยกเลิก
        assert mail.outbox == []
        assert audit_rows() == []

    def test_email_is_normalized_before_comparing(self, admin):
        user = make_user("same@example.com")

        outcome = update_user_by_admin(
            actor=admin, user_id=user.pk, updates={"email": "  SAME@Example.com "}
        )

        assert outcome.email_sent is None
        assert audit_rows() == []  # เป็นอีเมลเดิมหลัง normalize จึงไม่ใช่การเปลี่ยน

    def test_email_failure_still_changes_the_email(self, admin, monkeypatch):
        def boom(user, raw_token):
            raise RuntimeError("smtp down")

        monkeypatch.setattr("accounts.user_management.send_account_invite_email", boom)
        user = make_user("old@example.com", password=NO_PASSWORD)

        outcome = self.change(admin, user)

        assert outcome.email_sent is False
        user.refresh_from_db()
        assert user.email == self.NEW
        assert EmailVerificationToken.objects.filter(user=user, used_at=None).count() == 1


class TestSetActive:
    def test_deactivate_and_activate_are_logged(self, admin):
        user = make_user("user@example.com")

        set_user_active(actor=admin, user_id=user.pk, is_active=False)
        user.refresh_from_db()
        assert user.is_active is False
        assert status_of(user) == UserStatus.DISABLED

        set_user_active(actor=admin, user_id=user.pk, is_active=True)
        user.refresh_from_db()
        assert user.is_active is True

        assert [row.changes for row in audit_rows()] == [
            {"is_active": [True, False]},
            {"is_active": [False, True]},
        ]
        assert {row.action for row in audit_rows()} == {AuditAction.UPDATE}

    def test_repeating_is_harmless_and_not_logged_twice(self, admin):
        user = make_user("user@example.com")

        set_user_active(actor=admin, user_id=user.pk, is_active=False)
        set_user_active(actor=admin, user_id=user.pk, is_active=False)
        set_user_active(actor=admin, user_id=make_user("b@example.com").pk, is_active=True)

        assert len(audit_rows()) == 1

    def test_cannot_deactivate_self(self, admin):
        with pytest.raises(CannotDeactivateSelf):
            set_user_active(actor=admin, user_id=admin.pk, is_active=False)

        admin.refresh_from_db()
        assert admin.is_active is True
        assert audit_rows() == []

    def test_can_deactivate_another_admin_while_one_remains(self, admin):
        other = make_user("other-admin@example.com", role=Role.ADMIN)

        set_user_active(actor=admin, user_id=other.pk, is_active=False)

        other.refresh_from_db()
        assert other.is_active is False

    def test_cannot_deactivate_the_last_active_admin(self, admin):
        target = make_user("target-admin@example.com", role=Role.ADMIN)
        User.objects.filter(pk=admin.pk).update(role=Role.TEACHER)

        with pytest.raises(LastAdmin):
            set_user_active(actor=admin, user_id=target.pk, is_active=False)

        target.refresh_from_db()
        assert target.is_active is True

    def test_deactivating_kills_a_pending_invite_link(self, admin):
        user = make_user("new@example.com", password=NO_PASSWORD)
        raw = issue_token(user, RESET, INVITE_LIFETIME)

        set_user_active(actor=admin, user_id=user.pk, is_active=False)

        with pytest.raises(TokenInvalid):
            check_reset_token(raw)

    def test_unknown_user_is_404(self, admin):
        with pytest.raises(Http404):
            set_user_active(actor=admin, user_id=999999, is_active=False)


class TestResendInvite:
    def pending(self, age=timedelta(minutes=5)):
        """บัญชีที่รอตั้งรหัสผ่านพร้อมลิงก์ที่ออกไปแล้วเมื่อ age ที่แล้ว"""
        user = make_user("new@example.com", password=NO_PASSWORD)
        raw = issue_token(user, RESET, INVITE_LIFETIME)
        EmailVerificationToken.objects.filter(user=user).update(created_at=timezone.now() - age)
        return user, raw

    def test_sends_a_new_link_and_kills_the_old_one(self, admin):
        user, old_token = self.pending()

        outcome = resend_invite(actor=admin, user_id=user.pk)

        assert outcome.email_sent is True
        assert [m.to for m in mail.outbox] == [["new@example.com"]]
        with pytest.raises(TokenInvalid):
            peek_token(old_token, RESET)
        assert peek_token(token_in_last_email(), RESET) == user

    def test_is_logged_as_an_update_with_the_resend_event(self, admin):
        user, _ = self.pending()

        resend_invite(actor=admin, user_id=user.pk, audit_context={"ip": "10.0.0.5"})

        (row,) = audit_rows()
        assert row.action == AuditAction.UPDATE
        assert row.actor == admin
        assert row.changes is None
        assert row.context == {"ip": "10.0.0.5", "event": "resend_invite"}

    def test_too_soon_is_refused_without_email_or_log_and_keeps_the_link(self, admin):
        user, token = self.pending(age=timedelta(seconds=5))

        with pytest.raises(ResendTooSoon) as caught:
            resend_invite(actor=admin, user_id=user.pk)

        assert 1 <= caught.value.wait <= 60
        assert mail.outbox == []
        assert audit_rows() == []
        assert peek_token(token, RESET) == user

    def test_allowed_again_once_the_cooldown_has_passed(self, admin):
        user, _ = self.pending(age=timedelta(seconds=61))

        assert resend_invite(actor=admin, user_id=user.pk).email_sent is True

    def test_repeat_right_after_a_resend_is_refused(self, admin):
        user, _ = self.pending()
        resend_invite(actor=admin, user_id=user.pk)

        with pytest.raises(ResendTooSoon):
            resend_invite(actor=admin, user_id=user.pk)

        assert len(mail.outbox) == 1

    @pytest.mark.parametrize(
        "extra",
        [
            {},  # ใช้งานอยู่
            {"is_email_verified": False},  # สมัครเองยังไม่ยืนยันอีเมล
            {"password": NO_PASSWORD, "is_active": False},  # ปิดใช้งาน
        ],
    )
    def test_only_accounts_waiting_for_a_password_qualify(self, admin, extra):
        user = make_user("someone@example.com", **extra)

        with pytest.raises(InviteNotApplicable):
            resend_invite(actor=admin, user_id=user.pk)

        assert mail.outbox == []
        assert audit_rows() == []

    def test_email_failure_still_issues_the_link(self, admin, monkeypatch):
        def boom(user, raw_token):
            raise RuntimeError("smtp down")

        monkeypatch.setattr("accounts.user_management.send_account_invite_email", boom)
        user, old_token = self.pending()

        outcome = resend_invite(actor=admin, user_id=user.pk)

        assert outcome.email_sent is False
        with pytest.raises(TokenInvalid):
            peek_token(old_token, RESET)
        assert EmailVerificationToken.objects.filter(user=user, used_at=None).count() == 1

    def test_unknown_user_is_404(self, admin):
        with pytest.raises(Http404):
            resend_invite(actor=admin, user_id=999999)
