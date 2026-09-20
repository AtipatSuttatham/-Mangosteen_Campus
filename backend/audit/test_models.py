import pytest
from django.db import IntegrityError, transaction

from accounts.models import User
from audit.models import AuditAction, AuditLog

# ทุก test ในไฟล์นี้ใช้ฐานข้อมูลจริง (Postgres)
pytestmark = pytest.mark.django_db


def make_user(email="admin@example.com"):
    return User.objects.create_user(
        email=email, password="Str0ng-pass-123", first_name="สมชาย", last_name="ใจดี"
    )


class TestActions:
    def test_documented_actions_exist(self):
        # ชุด action ตาม docs/database.md §10 — ถ้าจะเพิ่ม/ลด ต้องแก้เอกสารและ migration พร้อมกัน
        assert set(AuditAction.values) == {
            "create",
            "update",
            "delete",
            "login",
            "logout",
            "impersonate_start",
            "impersonate_end",
            "publish",
            "enroll",
            "unenroll",
            "regrade",
        }

    def test_database_rejects_unknown_action(self):
        # bulk_create ข้าม save()/full_clean จึงชน constraint ของฐานข้อมูลตรง ๆ
        with pytest.raises(IntegrityError), transaction.atomic():
            AuditLog.objects.bulk_create([AuditLog(action="hack", object_repr="x")])

    def test_database_accepts_every_documented_action(self):
        AuditLog.objects.bulk_create([AuditLog(action=value) for value in AuditAction.values])

        assert AuditLog.objects.count() == len(AuditAction.values)


class TestRelations:
    def test_deleting_actor_keeps_the_log(self):
        actor = make_user()
        log = AuditLog.objects.create(actor=actor, action=AuditAction.LOGIN)

        actor.delete()

        log.refresh_from_db()
        assert log.actor is None

    def test_deleting_impersonator_keeps_the_log(self):
        real_admin = make_user("real@example.com")
        target = make_user("target@example.com")
        log = AuditLog.objects.create(
            actor=target, impersonated_by=real_admin, action=AuditAction.UPDATE
        )

        real_admin.delete()

        log.refresh_from_db()
        assert log.impersonated_by is None
        assert log.actor == target


class TestMeta:
    def test_newest_first(self):
        first = AuditLog.objects.create(action=AuditAction.LOGIN)
        second = AuditLog.objects.create(action=AuditAction.LOGOUT)

        assert list(AuditLog.objects.all()) == [second, first]

    def test_has_index_for_history_of_one_object(self):
        # ดึง "ประวัติทั้งหมดของวัตถุนี้" ต้องใช้ดัชนีนี้ (docs/database.md §10)
        index_fields = [list(index.fields) for index in AuditLog._meta.indexes]

        assert ["content_type", "object_id"] in index_fields

    def test_str_is_readable(self):
        log = AuditLog(action=AuditAction.CREATE, object_repr="somchai@example.com")

        assert str(log) == "create somchai@example.com"
