from rest_framework import serializers

from .admin_users import MAX_SEARCH_LENGTH
from .models import User
from .roles import Role
from .user_status import UserStatus, status_of


class AdminUserQuerySerializer(serializers.Serializer):
    """พารามิเตอร์ของรายชื่อผู้ใช้ (?role=&status=&search=) — ทุกตัวไม่บังคับ ค่าว่าง = ไม่กรอง

    ค่าที่ไม่รู้จักตอบ 400 พร้อม error_codes (ไม่เงียบแล้วคืนรายการที่ไม่ได้กรอง)
    เลขหน้า (?page=) ตรวจโดยตัวแบ่งหน้า (common/pagination.py)
    """

    role = serializers.ChoiceField(choices=Role.choices, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=UserStatus.choices, required=False, allow_blank=True)
    # CharField ตัดช่องว่างหัวท้ายให้เอง ข้อความว่างหรือมีแต่ช่องว่างจึงเท่ากับไม่ค้นหา
    search = serializers.CharField(required=False, allow_blank=True, max_length=MAX_SEARCH_LENGTH)


class AdminUserListSerializer(serializers.ModelSerializer):
    """ผู้ใช้ 1 แถวในหน้ารายชื่อของ Admin

    ระบุฟิลด์เป็น whitelist ทีละตัว: รหัสผ่าน (แฮช) และข้อมูลภายในอื่นไม่มีทางหลุดออกไป
    ไม่ดึงข้อมูลจากตารางอื่น จึงไม่มีคิวรีเพิ่มต่อแถว
    """

    # สถานะ 4 แบบ คำนวณจากฟิลด์ที่มี (ดู user_status.py)
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "student_or_staff_id",
            "role",
            "first_name",
            "last_name",
            "first_name_en",
            "last_name_en",
            "status",
            "is_active",
            "is_email_verified",
            "last_login",
            "date_joined",
        )
        read_only_fields = fields

    def get_status(self, user: User) -> str:
        return status_of(user)


class AdminUserDetailSerializer(AdminUserListSerializer):
    """ผู้ใช้ 1 คนสำหรับหน้าแก้ไข: ฟิลด์ของรายการ + ข้อมูลสำหรับ "ประวัติบัญชี"

    created_by = ผู้ที่สร้างบัญชีนี้ (null = สมัครเอง) — view ต้อง select_related("created_by")
    """

    created_by = serializers.SerializerMethodField()

    class Meta(AdminUserListSerializer.Meta):
        fields = (*AdminUserListSerializer.Meta.fields, "updated_at", "created_by")
        read_only_fields = fields

    def get_created_by(self, user: User) -> dict | None:
        creator = user.created_by
        if creator is None:
            return None
        return {"id": creator.pk, "full_name": creator.get_full_name()}
