from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext as _


def role_required(allowed_roles):
    """Decorator to restrict views to specific user roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in allowed_roles:
                messages.error(request, _('You do not have permission to access this page.'))
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Only administrators can access this view."""
    return role_required(['admin'])(view_func)


def teacher_or_admin_required(view_func):
    """Both administrators and teachers can access this view."""
    return role_required(['admin', 'teacher'])(view_func)
