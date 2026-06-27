"""
API v1 routes — เชื่อมกับโปรแกรมภายนอก
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('items', views.ItemViewSet, basename='item')
router.register('menu', views.MenuViewSet, basename='menu')
router.register('sales', views.DailySalesViewSet, basename='sales')
router.register('pl', views.MonthlyPLViewSet, basename='pl')
router.register('orders', views.OrderViewSet, basename='order')

app_name = 'api'

urlpatterns = [
    path('summary/', views.summary, name='summary'),
    path('', include(router.urls)),
]
