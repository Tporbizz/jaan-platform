from django.urls import path

from . import views

app_name = 'hr'

urlpatterns = [
    path('', views.shift_today, name='shift_today'),
    path('shifts/', views.shift_calendar, name='shift_calendar'),
    path('shifts/assign/', views.assign_shift, name='assign_shift'),
    path('api/today-staff/', views.api_today_staff, name='api_today_staff'),
]
