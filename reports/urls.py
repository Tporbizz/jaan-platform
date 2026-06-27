from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('pricing/', views.pricing_calculator, name='pricing_calculator'),
    path('variance/', views.variance_report, name='variance_report'),
    path('pl/', views.pl_dashboard, name='pl_dashboard'),
    path('sensibo/', views.sensibo_dashboard, name='sensibo_dashboard'),

    # Export CSV
    path('sales/export/', views.sales_export, name='sales_export'),
    path('pl/export/', views.pl_export, name='pl_export'),
]
