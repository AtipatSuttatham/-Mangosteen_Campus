from rest_framework import serializers

from .admin_users import MAX_SEARCH_LENGTH
from .models import User
from .registration import normalize_email
from .roles import Role
from .user_management import email_in_use, staff_id_in_use
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


class AdminUserWriteSerializer(serializers.Serializer):
    """ข้อมูลเข้าของการสร้างบัญชี (บังคับ role, first_name, last_name, email) และการแก้ไข (partial)

    รับเฉพาะฟิลด์ที่ประกาศไว้นี้ — ฟิลด์อื่นที่ส่งมา (password, is_active, is_staff, is_superuser,
    created_by, is_email_verified ฯลฯ) ถูกทิ้งทั้งหมด จึงตั้งสิทธิ์หรือรหัสผ่านผ่านทางนี้ไม่ได้
    (กัน mass assignment) ตรวจซ้ำของอีเมล/รหัสที่ระดับฟิลด์ เพื่อให้ผู้ใช้เห็นข้อผิดพลาดทุกช่อง
    พร้อมกันในรอบเดียว (ตอนแก้ไข instance = ผู้ใช้ที่กำลังแก้ จึงไม่นับซ้ำกับตัวเอง)
    """

    role = serializers.ChoiceField(choices=Role.choices)
    # CharField ตัดช่องว่างหัวท้ายให้เอง และไม่ยอมรับค่าว่าง
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    # ว่าง/null = ไม่มีรหัส (เก็บเป็น NULL) — ตอนแก้ ส่งค่าว่างเพื่อล้างรหัสได้
    student_or_staff_id = serializers.CharField(
        max_length=50, required=False, allow_blank=True, allow_null=True
    )
    first_name_en = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name_en = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def _exclude_pk(self) -> int | None:
        return self.instance.pk if self.instance is not None else None

    def validate_email(self, value: str) -> str:
        # อีเมลในฐานข้อมูลเป็นตัวพิมพ์เล็กเสมอ จึงตรวจซ้ำแบบไม่สนตัวพิมพ์
        value = normalize_email(value)
        if email_in_use(value, exclude_pk=self._exclude_pk()):
            raise serializers.ValidationError("อีเมลนี้ถูกใช้แล้ว", code="email_taken")
        return value

    def validate_student_or_staff_id(self, value: str | None) -> str | None:
        value = (value or "").strip()
        if not value:
            return None
        # รหัสห้ามมี @ (หน้า login ใช้ @ แยกอีเมลออกจากรหัส) — code เดียวกับตัวตรวจของโมเดล
        if "@" in value:
            raise serializers.ValidationError(
                "รหัสห้ามมีเครื่องหมาย @", code="staff_id_contains_at_sign"
            )
        if staff_id_in_use(value, exclude_pk=self._exclude_pk()):
            raise serializers.ValidationError("รหัสนี้ถูกใช้แล้ว", code="staff_id_taken")
        return value


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
