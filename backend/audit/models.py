from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q


class AuditAction(models.TextChoices):
    """ชนิดของการกระทำที่บันทึกใน Audit Log (ตาม docs/database.md §10 — เพิ่มได้ภายหลังพร้อม migration)"""

    CREATE = "create", "สร้าง"
    UPDATE = "update", "แก้ไข"
    DELETE = "delete", "ลบ"
    LOGIN = "login", "เข้าสู่ระบบ"
    LOGOUT = "logout", "ออกจากระบบ"
    IMPERSONATE_START = "impersonate_start", "เริ่มสวมสิทธิ์"
    IMPERSONATE_END = "impersonate_end", "สิ้นสุดการสวมสิทธิ์"
    PUBLISH = "publish", "เผยแพร่"
    ENROLL = "enroll", "ลงทะเบียนเข้ารายวิชา"
    UNENROLL = "unenroll", "ถอนออกจากรายวิชา"
    REGRADE = "regrade", "คำนวณคะแนนใหม่"


class AuditLog(models.Model):
    """ประวัติการกระทำที่เปลี่ยนแปลงข้อมูลสำคัญ 1 แถว = 1 การกระทำ (log กลางแบบ generic)

    เป็นตาราง "เขียนเพิ่มอย่างเดียว": โค้ดของระบบไม่มีทางแก้หรือลบแถว และหน้า Django admin เป็นแบบอ่านอย่างเดียว
    (การป้องกันระดับฐานข้อมูลอยู่ใน docs/pre-deploy-checklist.md) เขียนผ่าน audit.services.log_action เท่านั้น
    ห้ามเก็บรหัสผ่านหรือโทเคนลงในตารางนี้ — ใช้ field_changes ที่ระบุฟิลด์แบบ whitelist
    """

    # คนทำ (ว่าง = ระบบทำเอง) — ผู้ใช้ถูกลบแล้ว log ยังอยู่ (actor กลายเป็นว่าง)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ผู้กระทำ",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs_as_actor",
    )
    # Admin ตัวจริงเบื้องหลัง ถ้าอยู่ในโหมดสวมสิทธิ์ (actor = คนที่ถูกสวมสิทธิ์)
    impersonated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="สวมสิทธิ์โดย",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs_impersonated",
    )
    action = models.CharField("การกระทำ", max_length=20, choices=AuditAction.choices)

    # วัตถุที่ถูกกระทำ (ชี้แถวใดก็ได้ผ่าน ContentType) — ว่างได้ เช่น login/logout ที่ไม่มีวัตถุ
    # SET_NULL: ถ้าโมเดลปลายทางถูกลบออกจากระบบ ประวัติต้องไม่หายตาม (object_repr ยังบอกได้ว่าคืออะไร)
    content_type = models.ForeignKey(
        ContentType,
        verbose_name="ชนิดของวัตถุ",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    # pk ของวัตถุเก็บเป็นข้อความ เพราะโมเดลปลายทางอาจใช้ pk ชนิดอื่น
    object_id = models.CharField("รหัสวัตถุ", max_length=64, null=True, blank=True)
    # ข้อความอ่านออก ณ ตอนนั้น (snapshot) — ยังอ่านรู้เรื่องแม้วัตถุถูกแก้/ลบไปแล้ว
    object_repr = models.CharField("ข้อความแทนวัตถุ", max_length=255, blank=True, default="")

    # {"ฟิลด์": [ค่าเดิม, ค่าใหม่]} เฉพาะฟิลด์ที่เปลี่ยน (ใช้ field_changes สร้าง)
    changes = models.JSONField("ค่าที่เปลี่ยน", null=True, blank=True)
    # ที่มาของคำขอ: IP, user-agent, path (ใช้ request_context สร้าง)
    context = models.JSONField("บริบท", null=True, blank=True)

    created_at = models.DateTimeField("เวลา", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "ประวัติการกระทำ"
        verbose_name_plural = "ประวัติการกระทำ"
        # ใหม่สุดก่อน (id เป็นตัวตัดสินเมื่อเวลาเท่ากัน)
        ordering = ["-created_at", "-id"]
        indexes = [
            # ดึง "ประวัติทั้งหมดของวัตถุนี้" (docs/database.md §10)
            models.Index(fields=["content_type", "object_id"], name="audit_auditlog_target_idx"),
        ]
        constraints = [
            # ตาข่ายกันพลาดระดับฐานข้อมูล: action ต้องเป็นค่าที่กำหนดไว้เท่านั้น
            models.CheckConstraint(
                condition=Q(action__in=AuditAction.values),
                name="audit_auditlog_action_valid",
            ),
        ]

    def __str__(self):
        return f"{self.action} {self.object_repr}".strip()
