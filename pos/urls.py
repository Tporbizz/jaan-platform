from django.urls import path

from . import views

app_name = 'pos'

urlpatterns = [
    # POS Dashboard
    path('', views.pos_dashboard, name='pos_dashboard'),
    # Table Map
    path('tables/', views.table_map, name='table_map'),
    path('table/<int:table_id>/open/', views.open_table, name='open_table'),

    # Order
    path('order/<int:order_id>/', views.order_view, name='order_view'),
    path('order/<int:order_id>/add/', views.add_item, name='add_item'),
    path('order/<int:order_id>/add-custom/', views.add_custom_item, name='add_custom_item'),
    path('order/<int:order_id>/void/<int:item_id>/', views.void_item, name='void_item'),
    path('order/<int:order_id>/send/', views.send_to_kitchen, name='send_to_kitchen'),
    path('order/<int:order_id>/data/', views.order_data, name='order_data'),

    # Kitchen
    path('kitchen/', views.kitchen_display, name='kitchen_display'),
    path('kitchen/grid/', views.kitchen_grid, name='kitchen_grid'),
    path('kitchen/data/', views.kitchen_data, name='kitchen_data'),
    path('kitchen/ticket/<int:ticket_id>/', views.update_ticket, name='update_ticket'),

    # Payment
    path('payment/<int:order_id>/', views.payment_view, name='payment_view'),
    path('payment/<int:order_id>/process/', views.process_payment, name='process_payment'),
]
