from rest_framework import permissions

class ManagersOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Manager').exists() or request.user.is_superuser