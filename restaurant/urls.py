from django.urls import path

from . import views

app_name = 'restaurant'

urlpatterns = [
    path('', views.stock_dashboard, name='stock_dashboard'),
    path('export/', views.stock_export, name='stock_export'),
]
