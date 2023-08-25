from rest_framework import permissions


class IsAdminUserOrReadOnly(permissions.BasePermission):
    """Доступ только администратору, остальным чтение."""

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or (request.user.is_authenticated and request.user.is_admin)
        )


class IsAdminOrAuthorOrReadOnly(permissions.BasePermission):
    """Доступ автору и админу, остальным чтение."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and (
                request.user.is_admin
                or request.method in permissions.SAFE_METHODS
            )
        )


class IsOwnerAdmin(permissions.BasePermission):
    """Доступ владельцу и админу"""

    def has_permission(self, request, view, obj):
        return (
            obj.user == request.user and request.user.is_admin
        )
