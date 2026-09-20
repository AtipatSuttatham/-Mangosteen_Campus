from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """หน้าดู Audit Log ใน Django admin — อ่านอย่างเดียว (ใช้ตรวจจนกว่าจะมีหน้า Audit Log จริงของ Admin)

    ปิดการเพิ่ม/แก้/ลบทั้งหมด: log ที่แก้ได้ก็ไม่ใช่หลักฐาน (เขียนได้ทางเดียวคือ audit.services.log_action)
    """

    list_display = ("created_at", "actor", "action", "content_type", "object_repr")
    list_filter = ("action", "content_type")
    search_fields = ("object_repr", "object_id", "actor__email")
    date_hierarchy = "created_at"
    # กันคิวรีซ้ำต่อแถวตอนแสดงชื่อผู้กระทำและชนิดวัตถุ
    list_select_related = ("actor", "content_type")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
