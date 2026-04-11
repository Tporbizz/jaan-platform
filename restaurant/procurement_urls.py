from django.urls import path

from . import views

app_name = 'procurement'

urlpatterns = [
    path('reorder/', views.reorder_list, name='reorder_list'),
    path('po/', views.po_list, name='po_list'),
    path('receive/<int:po_id>/', views.goods_receipt, name='goods_receipt'),
    path('prices/', views.bulk_price_update, name='bulk_price_update'),
    path('api/create-pos/', views.create_pos_from_reorder, name='create_pos_from_reorder'),
]
