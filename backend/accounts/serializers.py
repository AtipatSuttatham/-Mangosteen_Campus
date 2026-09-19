from rest_framework import serializers

from .models import User


class LoginSerializer(serializers.Serializer):
    """ข้อมูลที่รับตอน login: ช่องเดียวรับทั้งรหัสนักศึกษา/พนักงานและอีเมล + รหัสผ่าน"""

    identifier = serializers.CharField(max_length=254)
    # ไม่ตัดช่องว่างของรหัสผ่าน (ช่องว่างอาจเป็นส่วนหนึ่งของรหัสผ่านจริง) และจำกัดความยาวกันส่งข้อมูลใหญ่เกินมาให้แฮช
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
