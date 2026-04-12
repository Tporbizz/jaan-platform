from django.urls import path

from . import views

app_name = 'hotel_integration'

urlpatterns = [
    path('', views.hotel_dashboard, name='hotel_dashboard'),
    path('room-lookup/', views.room_lookup, name='room_lookup'),
    path('import-csv/', views.import_guest_csv, name='import_guest_csv'),
    path('room-charge/', views.post_room_charge, name='post_room_charge'),
    path('bf-settlement/', views.bf_settlement, name='bf_settlement'),
]
