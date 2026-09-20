from django.apps import AppConfig


class AuditConfig(AppConfig):
    """ตั้งค่าแอป audit (ประวัติการกระทำที่เปลี่ยนแปลงข้อมูลสำคัญ — docs/database.md §10)"""

    # ให้ primary key เป็น BigAutoField ตามที่กำหนดใน docs/database.md
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
    verbose_name = "ประวัติการกระทำ"
