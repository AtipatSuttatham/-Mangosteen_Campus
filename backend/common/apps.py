from django.apps import AppConfig


class CommonConfig(AppConfig):
    """ตั้งค่าแอป common (ของที่ใช้ร่วมกันทุกแอป เช่น health check และ abstract model)"""

    # ให้ primary key ของ model ในแอปนี้เป็น BigAutoField ตามที่กำหนดใน docs/database.md
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
