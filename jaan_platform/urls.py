from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import include, path


def health_check(request):
    return JsonResponse({'status': 'ok'})


def landing(request):
    return render(request, 'landing.html')


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'dashboard.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        error = 'Username/Email หรือ Password ไม่ถูกต้อง'
    return render(request, 'login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


urlpatterns = [
    path('', landing, name='landing'),
    path('dashboard/', dashboard, name='dashboard'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('stock/', include('restaurant.urls', namespace='restaurant')),
    path('procurement/', include(('restaurant.procurement_urls', 'procurement'), namespace='procurement')),
    path('pos/', include('pos.urls', namespace='pos')),
    path('api/events/', include('events.urls', namespace='events')),
    path('api/hr/', include('hr.urls', namespace='hr')),
    path('api/hotel/', include('hotel_integration.urls', namespace='hotel_integration')),
    path('api/reports/', include('reports.urls', namespace='reports')),
    path('api/accounts/', include('accounts.urls', namespace='accounts')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass
