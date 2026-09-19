from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError

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


def test_handler_ignores_non_api_exceptions():
    # error ที่ไม่ใช่ของ API (เช่น บั๊กในโค้ด) ให้ Django จัดการต่อ ไม่ตอบเป็น JSON เอง
    assert api_exception_handler(ValueError("boom"), context={}) is None
