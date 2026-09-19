import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.models import User
from accounts.roles import Role

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db


def make_user(email="user@example.com", **extra):
    """สร้างผู้ใช้ทดสอบด้วยค่าพื้นฐานที่ครบ (ระบุเฉพาะส่วนที่แตกต่างในแต่ละ test)"""
    return User.objects.create_user(
        email=email,
        password="Str0ng-pass-123",
        first_name="สมชาย",
        last_name="ใจดี",
        **extra,
    )


def raw_user(**overrides):
    """ผู้ใช้ที่ยังไม่บันทึก ใช้กับ bulk_create เพื่อเลี่ยง save() และทดสอบ constraint ของฐานข้อมูลตรง ๆ"""
    data = {
        "email": "raw@example.com",
        "password": "x",
        "first_name": "ทดสอบ",
        "last_name": "ระบบ",
    }
    data.update(overrides)
    return User(**data)


class TestCreateUser:
    def test_email_is_stripped_and_lowercased(self):
        user = make_user(email="  Somchai@Example.COM  ")

        assert user.email == "somchai@example.com"

    def test_email_is_required(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="Str0ng-pass-123")

    def test_new_user_defaults_to_unverified_student(self):
        user = make_user()

        assert user.role == Role.STUDENT
        assert user.is_email_verified is False
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("Str0ng-pass-123")

    def test_user_without_password_has_unusable_password(self):
        # บัญชีที่ Admin สร้างให้ยังไม่มีรหัสผ่านจนกว่าเจ้าของกดลิงก์ตั้งรหัส
        user = User.objects.create_user(email="new@example.com", password=None)

        assert user.has_usable_password() is False

    def test_superuser_is_admin_and_verified(self):
        user = User.objects.create_superuser(email="root@example.com", password="Str0ng-pass-123")

        assert user.role == Role.ADMIN
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_email_verified is True

    def test_str_and_full_name(self):
        user = make_user()

        assert str(user) == "user@example.com"
        assert user.get_full_name() == "สมชาย ใจดี"


class TestEmailRules:
    def test_email_is_unique_ignoring_case(self):
        make_user(email="A@Example.com")

        with pytest.raises(IntegrityError), transaction.atomic():
            make_user(email="a@EXAMPLE.com")

    def test_database_rejects_uppercase_email(self):
        # เขียนเลี่ยง save() (bulk_create) — constraint ของฐานข้อมูลต้องกันไว้
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([raw_user(email="Upper@example.com")])


class TestStaffIdRules:
    def test_id_is_trimmed(self):
        user = make_user(student_or_staff_id="  650612001 ")

        assert user.student_or_staff_id == "650612001"

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_id_becomes_null(self, blank):
        user = make_user(student_or_staff_id=blank)

        assert user.student_or_staff_id is None

    def test_many_users_can_have_no_id(self):
        make_user(email="a@example.com")
        make_user(email="b@example.com")

        assert User.objects.filter(student_or_staff_id__isnull=True).count() == 2

    def test_id_is_case_sensitive(self):
        # S123 กับ s123 ถือเป็นคนละรหัส (ผู้ใช้ตัดสินใจให้แยกตัวพิมพ์)
        make_user(email="a@example.com", student_or_staff_id="S123")
        make_user(email="b@example.com", student_or_staff_id="s123")

        assert User.objects.filter(student_or_staff_id__in=["S123", "s123"]).count() == 2

    def test_id_must_be_unique(self):
        make_user(email="a@example.com", student_or_staff_id="S123")

        with pytest.raises(IntegrityError), transaction.atomic():
            make_user(email="b@example.com", student_or_staff_id="S123")

    def test_id_with_at_sign_fails_validation(self):
        # หน้า login ใช้ @ แยกอีเมลออกจากรหัส จึงห้ามมี @ ในรหัส
        user = User(email="a@example.com", first_name="ก", last_name="ข", student_or_staff_id="a@b")
        user.set_password("Str0ng-pass-123")

        with pytest.raises(ValidationError) as error:
            user.full_clean()

        assert "student_or_staff_id" in error.value.message_dict

    @pytest.mark.parametrize("bad_id", ["a@b", ""])
    def test_database_rejects_bad_id(self, bad_id):
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([raw_user(student_or_staff_id=bad_id)])


class TestRole:
    def test_database_rejects_unknown_role(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([raw_user(role="superhero")])


class TestTimestamps:
    def test_created_and_updated_are_set(self):
        user = make_user()

        assert user.created_at is not None
        assert user.updated_at is not None

    def test_updated_at_moves_forward_on_save(self):
        user = make_user()
        first_update = user.updated_at

        user.first_name = "สมหญิง"
        user.save()

        assert user.updated_at > first_update
