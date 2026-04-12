from django.urls import path

from . import settings_views as views

app_name = 'settings'

urlpatterns = [
    path('', views.settings_hub, name='hub'),

    # Items
    path('items/', views.item_list, name='item_list'),
    path('items/save/', views.item_save, name='item_save'),
    path('items/<int:item_id>/toggle/', views.item_toggle, name='item_toggle'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/save/', views.supplier_save, name='supplier_save'),
    path('suppliers/<int:supplier_id>/toggle/', views.supplier_toggle, name='supplier_toggle'),

    # Units
    path('units/', views.unit_list, name='unit_list'),
    path('units/save/', views.unit_save, name='unit_save'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/save/', views.category_save, name='category_save'),

    # Menu
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/save/', views.menu_save, name='menu_save'),
    path('menu/<int:menu_id>/toggle/', views.menu_toggle, name='menu_toggle'),

    # Employees
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/save/', views.employee_save, name='employee_save'),
    path('employees/<int:employee_id>/toggle/', views.employee_toggle, name='employee_toggle'),

    # Staff Accounts
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/save/', views.staff_save, name='staff_save'),
    path('staff/<int:staff_id>/toggle/', views.staff_toggle, name='staff_toggle'),
    path('staff/<int:staff_id>/reset-password/', views.staff_reset_password, name='staff_reset_password'),

    # Recipes
    path('recipes/', views.recipe_list, name='recipe_list'),
    path('recipes/save/', views.recipe_save, name='recipe_save'),
    path('recipes/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('recipes/<int:recipe_id>/add-ingredient/', views.recipe_add_ingredient, name='recipe_add_ingredient'),
    path('recipes/<int:recipe_id>/remove-ingredient/<int:ingredient_id>/', views.recipe_remove_ingredient, name='recipe_remove_ingredient'),
    path('recipes/<int:recipe_id>/api/cost/', views.recipe_api_cost, name='recipe_api_cost'),
]
