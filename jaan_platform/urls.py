from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('api/', include('restaurant.urls', namespace='restaurant')),
    path('api/pos/', include('pos.urls', namespace='pos')),
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
