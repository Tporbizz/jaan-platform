from django.urls import path

from . import views
from . import scan_views

app_name = 'procurement'

urlpatterns = [
    path('reorder/', views.reorder_list, name='reorder_list'),
    path('market-list/', views.market_list, name='market_list'),
    path('po/', views.po_list, name='po_list'),
    path('receive/<int:po_id>/', views.goods_receipt, name='goods_receipt'),
    path('prices/', views.bulk_price_update, name='bulk_price_update'),
    path('api/create-pos/', views.create_pos_from_reorder, name='create_pos_from_reorder'),

    # สแกนบิล supplier ด้วย AI (Claude vision)
    path('scan/', scan_views.scan_bill, name='scan_bill'),
    path('scan/extract/', scan_views.scan_bill_extract, name='scan_bill_extract'),
    path('scan/receive/', scan_views.scan_bill_receive, name='scan_bill_receive'),
]
