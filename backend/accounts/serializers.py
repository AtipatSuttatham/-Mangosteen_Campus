from rest_framework import serializers

from .models import User
from .password_rules import password_rule_errors


class LoginSerializer(serializers.Serializer):
    """ข้อมูลที่รับตอน login: ช่องเดียวรับทั้งรหัสนักศึกษา/พนักงานและอีเมล + รหัสผ่าน"""

    identifier = serializers.CharField(max_length=254)
    # ไม่ตัดช่องว่างของรหัสผ่าน (ช่องว่างอาจเป็นส่วนหนึ่งของรหัสผ่านจริง) และจำกัดความยาวกันส่งข้อมูลใหญ่เกินมาให้แฮช
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)


class RegisterSerializer(serializers.Serializer):
    """ข้อมูลที่รับตอนสมัครเอง: อีเมล + รหัสผ่าน + ชื่อ + นามสกุล

    ไม่รับ role / รหัสนักศึกษา / สิทธิ์ใด ๆ — ฟิลด์ที่ไม่ได้ประกาศไว้ที่นี่ถูกทิ้งทั้งหมด
    (ผู้สมัครเองเป็น student เสมอ ตั้งใน registration.py)
    """

    email = serializers.EmailField(max_length=254)
    # ไม่ตัดช่องว่างของรหัสผ่าน (เหมือนตอน login) และจำกัดความยาวกันส่งข้อมูลใหญ่เกินมาให้แฮช
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)
    # CharField ตัดช่องว่างหัวท้ายให้เอง และไม่ยอมรับค่าว่าง
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_password(self, value: str) -> str:
        """ตรวจกฎรหัสผ่านของระบบ (ตัวตรวจใน AUTH_PASSWORD_VALIDATORS) พร้อมข้อมูลผู้ใช้

        ส่งชื่อ/อีเมลที่กรอกมาให้ตัวตรวจด้วย เพื่อให้กฎ "ไม่คล้ายชื่อหรืออีเมลของคุณ" ทำงานจริง
        ทำที่ระดับฟิลด์ (ไม่ใช่ validate รวม) เพื่อให้ผู้ใช้เห็นข้อผิดพลาดของรหัสผ่านพร้อมกับ
        ข้อผิดพลาดของช่องอื่นในรอบเดียว ไม่ต้องแก้ทีละรอบ
        """
        candidate = User(
            email=str(self.initial_data.get("email", "")).strip().lower(),
            first_name=str(self.initial_data.get("first_name", "")).strip(),
            last_name=str(self.initial_data.get("last_name", "")).strip(),
        )
        # ส่งต่อพร้อม code ของแต่ละกฎ (เช่น password_too_short) ให้ frontend ใช้แปลข้อความ
        errors = password_rule_errors(value, candidate)
        if errors:
            raise serializers.ValidationError(errors)
        return value


class TokenSerializer(serializers.Serializer):
    """ข้อมูลที่รับเมื่อมีแค่โทเคนจากลิงก์ในอีเมล (ยืนยันอีเมล / ตรวจลิงก์ตั้งรหัสผ่าน)"""

    # โทเคนจริงยาวราว 43 ตัวอักษร — จำกัดไว้กันส่งข้อมูลใหญ่มาให้แฮชเปล่า ๆ
    token = serializers.CharField(max_length=256)


class EmailOnlySerializer(serializers.Serializer):
    """ข้อมูลที่รับเมื่อมีแค่อีเมล (ขอลิงก์ยืนยันใหม่ / ลืมรหัสผ่าน)"""

    email = serializers.EmailField(max_length=254)


class ResetPasswordSerializer(serializers.Serializer):
    """ข้อมูลที่รับตอนตั้งรหัสผ่านใหม่: โทเคนจากลิงก์ + รหัสผ่านใหม่

    กฎของรหัสผ่านตรวจใน password_reset.reset_password (ต้องรู้ผู้ใช้จากโทเคนก่อนจึงตรวจได้)
    """

    token = serializers.CharField(max_length=256)
    # ไม่ตัดช่องว่างของรหัสผ่าน และจำกัดความยาวกันส่งข้อมูลใหญ่เกินมาให้แฮช
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    """ข้อมูลผู้ใช้ที่ส่งให้ frontend (อ่านอย่างเดียว ไม่มีรหัสผ่านหรือสิทธิ์ภายใน)"""

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
            "is_email_verified",
            "avatar_url",
        )
        read_only_fields = fields
