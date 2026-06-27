"""
API Serializers — สำหรับเชื่อมกับโปรแกรมภายนอก (read-only)
"""
from rest_framework import serializers

from restaurant.models import Item, MenuItem
from reports.models import DailySalesRecord, MonthlyPL
from pos.models import Order


class ItemSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name', default=None, read_only=True)
    unit = serializers.CharField(source='unit.abbreviation', default=None, read_only=True)
    supplier = serializers.CharField(source='default_supplier.name', default=None, read_only=True)
    stock_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Item
        fields = ['id', 'code', 'name', 'category', 'unit', 'current_stock',
                  'min_stock', 'max_stock', 'cost_per_unit', 'stock_value',
                  'stock_status', 'supplier']


class MenuSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='get_menu_category_display', read_only=True)
    food_cost_pct = serializers.DecimalField(max_digits=6, decimal_places=1, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'name_en', 'category', 'selling_price',
                  'food_cost_pct', 'is_available']


class DailySalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySalesRecord
        fields = ['date', 'total_revenue', 'dine_in_revenue', 'beverage_revenue',
                  'total_covers', 'avg_check', 'food_cost_actual']


class MonthlyPLSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyPL
        fields = ['month', 'year', 'total_revenue', 'food_cost_actual', 'waste_cost',
                  'labour_cost', 'gross_profit', 'net_profit', 'food_cost_pct',
                  'labour_cost_pct', 'prime_cost_pct']


class OrderSerializer(serializers.ModelSerializer):
    table = serializers.CharField(source='table.number', default=None, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'table', 'status', 'guest_count',
                  'subtotal', 'total', 'opened_at', 'closed_at']
