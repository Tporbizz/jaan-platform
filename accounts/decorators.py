"""
Department-based permission decorators for Jaan Restaurant OS

แผนก:
  GM   — เข้าถึงทุกอย่าง (Settings, P&L, Food Cost)
  Manager — Stock, Reports, POS, Kitchen
  FB   — POS, Payment, เครื่องดื่ม (ไม่เข้า Kitchen Display)
  KT   — Kitchen Display, เวลาทำอาหาร (ไม่เข้า POS/Payment)
"""
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect, render


def _check_auth(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return None


def require_manager(view_func):
    """Owner/Manager เท่านั้น"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        r = _check_auth(request)
        if r:
            return r
        if not request.user.is_manager:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_gm(view_func):
    """GM/Owner เท่านั้น — Settings, P&L, Food Cost"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        r = _check_auth(request)
        if r:
            return r
        if not request.user.can_access_settings:
            return render(request, 'includes/no_access.html', {
                'message': 'เฉพาะ GM/Owner เท่านั้น',
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_pos(view_func):
    """FB, Manager, GM — POS access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        r = _check_auth(request)
        if r:
            return r
        if not request.user.can_access_pos:
            return render(request, 'includes/no_access.html', {
                'message': 'เฉพาะพนักงานหน้าร้าน (FB), Manager หรือ GM',
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_kitchen(view_func):
    """KT, Manager, GM — Kitchen Display access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        r = _check_auth(request)
        if r:
            return r
        if not request.user.can_access_kitchen:
            return render(request, 'includes/no_access.html', {
                'message': 'เฉพาะพนักงานครัว (KT), Manager หรือ GM',
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_stock(view_func):
    """Manager, GM — Stock/Reports access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        r = _check_auth(request)
        if r:
            return r
        if not request.user.can_access_stock:
            return render(request, 'includes/no_access.html', {
                'message': 'เฉพาะ Manager หรือ GM',
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
