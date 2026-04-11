from django.urls import path

from . import views

app_name = 'restaurant'

urlpatterns = [
    path('stock/', views.stock_dashboard, name='stock_dashboard'),
]
