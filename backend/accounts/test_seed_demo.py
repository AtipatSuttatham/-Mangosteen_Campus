import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from accounts.management.commands.seed_demo import DEMO_ACCOUNTS
from accounts.models import User
from accounts.roles import Role

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db

PASSWORD = "Demo-Pass-2568!"


@pytest.fixture(autouse=True)
def dev_mode_with_password(settings, monkeypatch):
    """ค่าเริ่มต้นของทุก test: โหมด dev + ตั้ง DEMO_PASSWORD (test ที่ต้องการกรณีอื่นจะแก้ทับเอง)"""
    settings.DEBUG = True
    monkeypatch.setenv("DEMO_PASSWORD", PASSWORD)


class TestGuards:
    def test_refuses_when_not_debug(self, settings):
        settings.DEBUG = False

        with pytest.raises(CommandError, match="DJANGO_DEBUG=1"):
            call_command("seed_demo")

        assert User.objects.count() == 0

    def test_refuses_when_password_not_set(self, monkeypatch):
        monkeypatch.delenv("DEMO_PASSWORD")

        with pytest.raises(CommandError, match="DEMO_PASSWORD"):
            call_command("seed_demo")

        assert User.objects.count() == 0

    def test_refuses_weak_password(self, monkeypatch):
        monkeypatch.setenv("DEMO_PASSWORD", "12345678")

        with pytest.raises(CommandError, match="not acceptable"):
            call_command("seed_demo")

        assert User.objects.count() == 0


class TestSeed:
    def test_creates_one_verified_account_per_role(self):
        call_command("seed_demo")

        assert User.objects.count() == len(DEMO_ACCOUNTS)
        assert set(User.objects.values_list("role", flat=True)) == {
            Role.ADMIN,
            Role.TEACHER,
            Role.STUDENT,
        }
        for user in User.objects.all():
            assert user.is_email_verified
            assert user.is_active
            # บัญชีทดสอบไม่ต้องเข้า Django admin (ให้สิทธิ์น้อยที่สุด)
            assert not user.is_staff
            assert user.check_password(PASSWORD)

    def test_running_twice_does_not_duplicate(self):
        call_command("seed_demo")
        call_command("seed_demo")

        assert User.objects.count() == len(DEMO_ACCOUNTS)

    def test_rerun_resets_password_and_role_and_reactivates(self, monkeypatch):
        call_command("seed_demo")
        teacher = User.objects.get(student_or_staff_id="TCH001")
        teacher.role = Role.STUDENT
        teacher.is_active = False
        teacher.save()
        monkeypatch.setenv("DEMO_PASSWORD", "Another-Pass-9876!")

        call_command("seed_demo")

        teacher.refresh_from_db()
        assert teacher.role == Role.TEACHER
        assert teacher.is_active
        assert teacher.check_password("Another-Pass-9876!")

    def test_stops_without_touching_an_id_held_by_another_account(self):
        User.objects.create_user(
            email="someone.else@example.com",
            password=PASSWORD,
            first_name="คนอื่น",
            last_name="ของจริง",
            student_or_staff_id="ADM001",
        )

        with pytest.raises(CommandError, match="ADM001"):
            call_command("seed_demo")

        # ธุรกรรมเดียว: ไม่เหลือบัญชีทดสอบที่สร้างค้าง และบัญชีเดิมไม่ถูกแตะ
        assert User.objects.count() == 1
        assert User.objects.get().email == "someone.else@example.com"

    @pytest.mark.parametrize("account", DEMO_ACCOUNTS, ids=lambda a: a["role"])
    def test_can_log_in_with_id_and_with_email(self, account):
        call_command("seed_demo")
        client = APIClient()

        for identifier in (account["student_or_staff_id"], account["email"]):
            response = client.post(
                "/api/auth/login/",
                {"identifier": identifier, "password": PASSWORD},
                format="json",
            )
            assert response.status_code == 200
            assert response.json()["user"]["role"] == account["role"]
