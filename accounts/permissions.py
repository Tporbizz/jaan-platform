from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Owner เห็นทุกอย่าง"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'owner'


class IsManagerOrAbove(BasePermission):
    """Manager เห็น reports + cost"""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ('owner', 'manager')
        )


class IsStaffOrAbove(BasePermission):
    """Staff เห็น POS + stock"""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ('owner', 'manager', 'staff')
        )


class TenantAccessMixin:
    """
    Mixin สำหรับ ViewSet — filter queryset ด้วย tenant ของ user
    ใช้กับทุก model ที่มี tenant FK
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)
