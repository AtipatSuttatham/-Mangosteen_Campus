from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """ตั้งค่าแอป accounts (ผู้ใช้ และต่อไปคือการล็อกอิน/สมัคร/ยืนยันอีเมล)"""

    # ให้ primary key เป็น BigAutoField ตามที่กำหนดใน docs/database.md
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "บัญชีผู้ใช้"
