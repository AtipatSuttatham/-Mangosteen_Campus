from rest_framework.test import APIClient


def test_health_returns_ok_without_login():
    """health endpoint ตอบ 200 โดยไม่ต้อง login และไม่ต้องใช้ฐานข้อมูล"""
    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
