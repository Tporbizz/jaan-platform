from django.shortcuts import redirect


class LoginRequiredMiddleware:
    """Redirect unauthenticated users to login for all pages except whitelist."""

    PUBLIC_PATHS = (
        '/login/',
        '/logout/',
        '/health/',
        '/admin/login/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(p) for p in self.PUBLIC_PATHS):
                return redirect(f'/login/?next={path}')
        return self.get_response(request)
