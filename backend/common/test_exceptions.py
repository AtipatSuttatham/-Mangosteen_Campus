from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import (
    APIException,
    ErrorDetail,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)

from common.exceptions import api_exception_handler


def test_handler_adds_code_to_generic_api_errors():
    response = api_exception_handler(PermissionDenied(), context={})

    assert response.status_code == 403
    assert response.data["code"] == "permission_denied"
    assert "detail" in response.data


def test_handler_keeps_code_of_authentication_errors():
    response = api_exception_handler(NotAuthenticated(), context={})

    assert response.data["code"] == "not_authenticated"


def test_handler_wraps_validation_errors():
    exc = ValidationError({"identifier": ["ต้องกรอก"]})

    response = api_exception_handler(exc, context={})

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert response.data["errors"] == {"identifier": ["ต้องกรอก"]}


def test_handler_adds_error_codes_per_field_for_validation_errors():
    # error_codes มีโครงเดียวกับ errors แต่เป็นรหัสของแต่ละกฎ ให้ frontend แปลข้อความรายกฎได้
    exc = ValidationError(
        {"password": [ErrorDetail("สั้นไป", code="password_too_short")], "email": ["ผิด"]}
    )

    response = api_exception_handler(exc, context={})

    assert response.data["error_codes"] == {
        "password": ["password_too_short"],
        "email": ["invalid"],
    }


def test_handler_adds_retry_after_when_the_error_has_a_wait():
    class Busy(APIException):
        status_code = 429
        default_code = "busy"
        wait = 42

    response = api_exception_handler(Busy(), context={})

    assert response.status_code == 429
    assert response.data["code"] == "busy"
    assert response.data["retry_after"] == 42
    # header มาตรฐานของ DRF ใส่ให้เองเมื่อมี wait
    assert response["Retry-After"] == "42"


def test_handler_has_no_retry_after_for_ordinary_errors():
    response = api_exception_handler(PermissionDenied(), context={})

    assert "retry_after" not in response.data


def test_handler_adds_code_to_django_404():
    # ค้นหาแถวด้วย id ที่ไม่มีอยู่ (get_object_or_404) โยน Http404 ของ Django ซึ่งไม่ใช่ APIException
    response = api_exception_handler(Http404(), context={})

    assert response.status_code == 404
    assert response.data["code"] == "not_found"


def test_handler_adds_code_to_django_permission_denied():
    response = api_exception_handler(DjangoPermissionDenied(), context={})

    assert response.status_code == 403
    assert response.data["code"] == "permission_denied"


def test_handler_ignores_non_api_exceptions():
    # error ที่ไม่ใช่ของ API (เช่น บั๊กในโค้ด) ให้ Django จัดการต่อ ไม่ตอบเป็น JSON เอง
    assert api_exception_handler(ValueError("boom"), context={}) is None
