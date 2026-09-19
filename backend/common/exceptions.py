from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """ตัวจัดการ error ของ API ทั้งระบบ — ทำให้ทุก error มี "code" ที่ frontend ใช้แปลภาษาได้

    รูปแบบที่ตอบกลับ:
    - error ทั่วไป:        {"code": "invalid_credentials", "detail": "ข้อความ"}
    - ข้อมูลที่ส่งมาไม่ถูก:  {"code": "validation_error", "errors": {"ชื่อฟิลด์": [...]},
                            "error_codes": {"ชื่อฟิลด์": ["password_too_short", ...]}}
    frontend ควรใช้ "code" เป็นกุญแจแปลข้อความ ไม่แสดง "detail" จาก backend ตรง ๆ
    ส่วน "error_codes" (โครงเดียวกับ "errors") ไว้ให้แปลข้อความรายกฎของแต่ละช่อง เช่น กฎรหัสผ่านข้อไหนไม่ผ่าน
    """
    # ให้ DRF สร้าง response มาตรฐาน (รวมสถานะ HTTP และ header เช่น WWW-Authenticate) ก่อน
    response = exception_handler(exc, context)
    if response is None or not isinstance(exc, APIException):
        return response

    if isinstance(exc, ValidationError):
        response.data = {
            "code": "validation_error",
            "errors": response.data,
            "error_codes": exc.get_codes(),
        }
        return response

    codes = exc.get_codes()
    if isinstance(response.data, dict) and isinstance(codes, str):
        response.data["code"] = codes
    return response
