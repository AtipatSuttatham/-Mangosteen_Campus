from rest_framework.permissions import BasePermission

from .roles import Role


class IsAdminRole(BasePermission):
    """อนุญาตเฉพาะผู้ใช้ที่ล็อกอินแล้วและมีบทบาทระดับระบบเป็น admin

    ตรวจจาก "ผู้ใช้ที่โหลดจากฐานข้อมูลในคำขอนี้" (request.user) ไม่ใช่ role ที่อยู่ใน token
    จึงมีผลทันทีเมื่อบทบาทเปลี่ยน: Admin ที่ถูกลดบทบาทแล้วยังถือ token เดิม (อายุสูงสุด 15 นาที) จะโดนปฏิเสธ
    (ตามกติกาใน CLAUDE.md: สิทธิ์จริงของข้อมูล backend ตรวจจากฐานข้อมูลทุกครั้ง)

    ไม่ล็อกอิน → 401 (ตัวยืนยันตัวตนตอบ) / ล็อกอินแล้วแต่ไม่ใช่ admin → 403 code "permission_denied"
    """

    message = "ต้องเป็นผู้ดูแลระบบเท่านั้น"

    def has_permission(self, request, view):
        user = request.user
        # is_active ตรวจซ้ำแม้ตัวยืนยันตัวตนกรองให้แล้ว: ตัวตรวจสิทธิ์ต้องไม่พึ่งพฤติกรรมของชั้นอื่น
        return bool(user and user.is_authenticated and user.is_active and user.role == Role.ADMIN)
