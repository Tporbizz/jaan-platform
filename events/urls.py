from django.urls import path

from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('create/', views.event_create, name='event_create'),
    path('<int:session_id>/', views.event_dashboard, name='event_dashboard'),
    path('<int:session_id>/toggle/', views.event_toggle, name='event_toggle'),
    # Public (no login)
    path('qr/<uuid:session_token>/', views.public_menu, name='public_menu'),
    path('qr/<uuid:session_token>/order/', views.public_order, name='public_order'),
    path('qr/<uuid:session_token>/pay/<int:order_id>/', views.public_pay, name='public_pay'),
]
