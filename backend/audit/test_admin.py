import pytest
from django.urls import reverse

from accounts.models import User
from audit.models import AuditAction, AuditLog

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db


@pytest.fixture
def superuser_client(client):
    """client ที่ล็อกอินหน้า Django admin ด้วยผู้ดูแลระบบสูงสุด"""
    superuser = User.objects.create_superuser(
        email="root@example.com", password="Str0ng-pass-123", first_name="ราก", last_name="ระบบ"
    )
    client.force_login(superuser)
    return client


class TestAuditLogAdmin:
    def test_list_page_shows_logs(self, superuser_client):
        AuditLog.objects.create(action=AuditAction.CREATE, object_repr="new@example.com")

        response = superuser_client.get(reverse("admin:audit_auditlog_changelist"))

        assert response.status_code == 200
        assert "new@example.com" in response.content.decode()

    def test_cannot_add_logs(self, superuser_client):
        response = superuser_client.get(reverse("admin:audit_auditlog_add"))

        assert response.status_code == 403

    def test_cannot_change_or_delete_a_log(self, superuser_client):
        log = AuditLog.objects.create(action=AuditAction.CREATE, object_repr="x")

        # หน้าเปิดดูได้ (อ่านอย่างเดียว) แต่สั่งลบไม่ได้ และแถวต้องยังอยู่
        assert (
            superuser_client.get(reverse("admin:audit_auditlog_change", args=[log.pk])).status_code
            == 200
        )
        assert (
            superuser_client.post(reverse("admin:audit_auditlog_delete", args=[log.pk])).status_code
            == 403
        )
        assert AuditLog.objects.filter(pk=log.pk).exists()
