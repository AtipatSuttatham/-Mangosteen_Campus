from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """ตรวจว่า backend ทำงานอยู่ — ไม่ต้อง login และไม่แตะฐานข้อมูล (ใช้กับ CI / monitor)"""
    return Response({"status": "ok"})
