"""
Settings Hub — In-app CRUD for Items, Suppliers, Units, Categories, Employees, Menu
ไม่ต้องเข้า /admin/ อีก — จัดการทุกอย่างจาก Dashboard
"""
import json
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import require_gm as require_manager
from .models import Category, Item, MenuItem, Recipe, RecipeItem, Supplier, Unit


# =============================================================================
# Settings Hub — Main Page
# =============================================================================

def settings_hub(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    if not tenant:
        return render(request, 'settings/hub.html', {'no_tenant': True})

    context = {
        'items_count': Item.objects.filter(tenant=tenant).count(),
        'suppliers_count': Supplier.objects.filter(tenant=tenant, is_active=True).count(),
        'units_count': Unit.objects.filter(tenant=tenant).count(),
        'categories_count': Category.objects.filter(tenant=tenant).count(),
        'menu_count': MenuItem.objects.filter(tenant=tenant).count(),
        'recipe_count': Recipe.objects.filter(tenant=tenant).count(),
    }

    # Employee count (lazy import to avoid circular)
    from hr.models import Employee
    context['employees_count'] = Employee.objects.filter(tenant=tenant, is_active=True).count()

    # Staff accounts count
    from accounts.models import User
    context['staff_count'] = User.objects.filter(tenant=tenant, is_active=True).count()

    return render(request, 'settings/hub.html', context)


# =============================================================================
# Items CRUD
# =============================================================================

def item_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    items = Item.objects.filter(tenant=tenant).select_related('category', 'unit', 'default_supplier')

    cat_filter = request.GET.get('cat', '')
    if cat_filter:
        items = items.filter(category_id=cat_filter)

    search = request.GET.get('q', '')
    if search:
        items = items.filter(name__icontains=search)

    categories = Category.objects.filter(tenant=tenant)
    units = Unit.objects.filter(tenant=tenant)
    suppliers = Supplier.objects.filter(tenant=tenant, is_active=True)

    context = {
        'items': items,
        'categories': categories,
        'units': units,
        'suppliers': suppliers,
        'cat_filter': cat_filter,
        'search': search,
    }
    return render(request, 'settings/item_list.html', context)


@require_manager
@require_POST
def item_save(request):
    tenant = request.user.tenant
    item_id = request.POST.get('item_id', '').strip()

    if item_id:
        item = get_object_or_404(Item, id=item_id, tenant=tenant)
    else:
        item = Item(tenant=tenant)

    item.name = request.POST.get('name', '').strip()
    item.category_id = request.POST.get('category') or None
    item.unit_id = request.POST.get('unit')
    item.default_supplier_id = request.POST.get('supplier') or None
    item.min_stock = Decimal(request.POST.get('min_stock', '0') or '0')
    item.max_stock = Decimal(request.POST.get('max_stock', '0') or '0')
    item.cost_per_unit = Decimal(request.POST.get('cost_per_unit', '0') or '0')

    if not item_id:
        item.current_stock = Decimal(request.POST.get('current_stock', '0') or '0')

    item.save()
    return redirect('settings:item_list')


@require_manager
@require_POST
def item_toggle(request, item_id):
    tenant = request.user.tenant
    item = get_object_or_404(Item, id=item_id, tenant=tenant)
    item.is_active = not item.is_active
    item.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'is_active': item.is_active})


# =============================================================================
# Suppliers CRUD
# =============================================================================

def supplier_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    suppliers = Supplier.objects.filter(tenant=tenant)
    return render(request, 'settings/supplier_list.html', {'suppliers': suppliers})


@require_manager
@require_POST
def supplier_save(request):
    tenant = request.user.tenant
    sid = request.POST.get('supplier_id', '').strip()

    if sid:
        supplier = get_object_or_404(Supplier, id=sid, tenant=tenant)
    else:
        supplier = Supplier(tenant=tenant)

    supplier.name = request.POST.get('name', '').strip()
    supplier.contact_person = request.POST.get('contact_person', '').strip()
    supplier.phone = request.POST.get('phone', '').strip()
    supplier.line_id = request.POST.get('line_id', '').strip()
    supplier.notes = request.POST.get('notes', '').strip()
    supplier.save()
    return redirect('settings:supplier_list')


@require_manager
@require_POST
def supplier_toggle(request, supplier_id):
    tenant = request.user.tenant
    supplier = get_object_or_404(Supplier, id=supplier_id, tenant=tenant)
    supplier.is_active = not supplier.is_active
    supplier.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'is_active': supplier.is_active})


# =============================================================================
# Units CRUD
# =============================================================================

def unit_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    units = Unit.objects.filter(tenant=tenant)
    return render(request, 'settings/unit_list.html', {'units': units})


@require_manager
@require_POST
def unit_save(request):
    tenant = request.user.tenant
    uid = request.POST.get('unit_id', '').strip()

    if uid:
        unit = get_object_or_404(Unit, id=uid, tenant=tenant)
    else:
        unit = Unit(tenant=tenant)

    unit.name = request.POST.get('name', '').strip()
    unit.abbreviation = request.POST.get('abbreviation', '').strip()
    unit.save()
    return redirect('settings:unit_list')


# =============================================================================
# Categories CRUD
# =============================================================================

def category_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    categories = Category.objects.filter(tenant=tenant).annotate(
        item_count=models.Count('items'),
    )
    return render(request, 'settings/category_list.html', {'categories': categories})


@require_manager
@require_POST
def category_save(request):
    tenant = request.user.tenant
    cid = request.POST.get('category_id', '').strip()

    if cid:
        cat = get_object_or_404(Category, id=cid, tenant=tenant)
    else:
        cat = Category(tenant=tenant)

    cat.name = request.POST.get('name', '').strip()
    cat.sort_order = int(request.POST.get('sort_order', '0') or '0')
    cat.save()
    return redirect('settings:category_list')


# =============================================================================
# Menu Items CRUD
# =============================================================================

def menu_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    menus = MenuItem.objects.filter(tenant=tenant).select_related('recipe')
    recipes = Recipe.objects.filter(tenant=tenant)

    context = {
        'menus': menus,
        'recipes': recipes,
        'menu_categories': MenuItem.MenuCategory.choices,
    }
    return render(request, 'settings/menu_list.html', context)


@require_manager
@require_POST
def menu_save(request):
    tenant = request.user.tenant
    mid = request.POST.get('menu_id', '').strip()

    if mid:
        menu = get_object_or_404(MenuItem, id=mid, tenant=tenant)
    else:
        menu = MenuItem(tenant=tenant)

    menu.name = request.POST.get('name', '').strip()
    menu.name_en = request.POST.get('name_en', '').strip()
    menu.menu_category = request.POST.get('menu_category', 'main')
    menu.selling_price = Decimal(request.POST.get('selling_price', '0') or '0')
    menu.recipe_id = request.POST.get('recipe') or None
    menu.is_available = request.POST.get('is_available') == 'on'
    menu.sort_order = int(request.POST.get('sort_order', '0') or '0')
    if request.FILES.get('image'):
        menu.image = request.FILES['image']
    menu.save()
    return redirect('settings:menu_list')


@require_manager
@require_POST
def menu_toggle(request, menu_id):
    tenant = request.user.tenant
    menu = get_object_or_404(MenuItem, id=menu_id, tenant=tenant)
    menu.is_available = not menu.is_available
    menu.save(update_fields=['is_available'])
    return JsonResponse({'ok': True, 'is_available': menu.is_available})


# =============================================================================
# Employees CRUD
# =============================================================================

def employee_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    from hr.models import Employee
    employees = Employee.objects.filter(tenant=tenant)

    context = {
        'employees': employees,
        'positions': Employee.Position.choices,
    }
    return render(request, 'settings/employee_list.html', context)


@require_manager
@require_POST
def employee_save(request):
    tenant = request.user.tenant
    from hr.models import Employee

    eid = request.POST.get('employee_id', '').strip()
    if eid:
        emp = get_object_or_404(Employee, id=eid, tenant=tenant)
    else:
        emp = Employee(tenant=tenant)

    emp.first_name = request.POST.get('first_name', '').strip()
    emp.last_name = request.POST.get('last_name', '').strip()
    emp.nickname = request.POST.get('nickname', '').strip()
    emp.position = request.POST.get('position', 'server')
    emp.phone = request.POST.get('phone', '').strip()
    emp.base_salary = Decimal(request.POST.get('base_salary', '0') or '0')
    emp.hourly_rate = Decimal(request.POST.get('hourly_rate', '0') or '0')
    emp.ot_rate = Decimal(request.POST.get('ot_rate', '0') or '0')
    emp.save()
    return redirect('settings:employee_list')


@require_manager
@require_POST
def employee_toggle(request, employee_id):
    tenant = request.user.tenant
    from hr.models import Employee
    emp = get_object_or_404(Employee, id=employee_id, tenant=tenant)
    emp.is_active = not emp.is_active
    emp.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'is_active': emp.is_active})


# Need models import for Count
from django.db import models


# =============================================================================
# Staff Accounts — สร้าง/แก้ไข login พนักงาน (User accounts)
# =============================================================================

@require_manager
def staff_list(request):
    tenant = request.user.tenant
    from accounts.models import User
    staff = User.objects.filter(tenant=tenant).order_by('department', 'first_name')
    dept_summary = []
    for code, label in User.Department.choices:
        dept_summary.append({'code': code, 'label': label, 'count': staff.filter(department=code).count()})
    context = {
        'staff': staff,
        'roles': User.Role.choices,
        'departments': User.Department.choices,
        'dept_summary': dept_summary,
    }
    return render(request, 'settings/staff_list.html', context)


@require_manager
@require_POST
def staff_save(request):
    tenant = request.user.tenant
    from accounts.models import User

    staff_id = request.POST.get('staff_id', '').strip()
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    role = request.POST.get('role', 'staff')
    department = request.POST.get('department', 'fb')
    phone = request.POST.get('phone', '').strip()

    if staff_id:
        user = get_object_or_404(User, id=staff_id, tenant=tenant)
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.department = department
        user.phone = phone
        if password:
            user.set_password(password)
        user.save()
    else:
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username นี้มีอยู่แล้ว'}, status=400)
        user = User.objects.create_user(
            username=username,
            password=password or 'jaan1234',
            first_name=first_name,
            last_name=last_name,
            role=role,
            department=department,
            phone=phone,
            tenant=tenant,
        )
    return redirect('settings:staff_list')


@require_manager
@require_POST
def staff_toggle(request, staff_id):
    tenant = request.user.tenant
    from accounts.models import User
    user = get_object_or_404(User, id=staff_id, tenant=tenant)
    if user == request.user:
        return JsonResponse({'error': 'ไม่สามารถปิดบัญชีตัวเอง'}, status=400)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'is_active': user.is_active})


@require_manager
@require_POST
def staff_reset_password(request, staff_id):
    tenant = request.user.tenant
    from accounts.models import User
    user = get_object_or_404(User, id=staff_id, tenant=tenant)
    new_pw = request.POST.get('password', 'jaan1234').strip() or 'jaan1234'
    user.set_password(new_pw)
    user.save()
    return JsonResponse({'ok': True})


# =============================================================================
# Recipe Builder — สร้าง/แก้สูตรอาหาร + คำนวณต้นทุน
# =============================================================================

def recipe_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    recipes = Recipe.objects.filter(tenant=tenant).prefetch_related('ingredients__item', 'ingredients__unit', 'menu_items')
    items = Item.objects.filter(tenant=tenant, is_active=True).select_related('unit')
    units = Unit.objects.filter(tenant=tenant)

    context = {
        'recipes': recipes,
        'items': items,
        'units': units,
    }
    return render(request, 'settings/recipe_list.html', context)


def recipe_detail(request, recipe_id):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    recipe = get_object_or_404(Recipe, id=recipe_id, tenant=tenant)
    ingredients = recipe.ingredients.select_related('item', 'item__unit', 'unit')
    items = Item.objects.filter(tenant=tenant, is_active=True).select_related('unit')
    units = Unit.objects.filter(tenant=tenant)
    menus = recipe.menu_items.all()

    # ข้อมูลวัตถุดิบสำหรับช่องค้นหา (ค้นด้วยชื่อ/รหัส + auto หน่วย + พรีวิวต้นทุน)
    items_json = [
        {
            'id': it.id, 'code': it.code, 'name': it.name,
            'cost': float(it.cost_per_unit), 'unit_id': it.unit_id,
            'unit': it.unit.abbreviation,
        }
        for it in items
    ]

    context = {
        'recipe': recipe,
        'ingredients': ingredients,
        'items': items,
        'units': units,
        'menus': menus,
        'items_json': items_json,
        'total_cost': recipe.calculate_cost(),
    }
    return render(request, 'settings/recipe_detail.html', context)


@require_manager
@require_POST
def recipe_save(request):
    tenant = request.user.tenant
    rid = request.POST.get('recipe_id', '').strip()

    if rid:
        recipe = get_object_or_404(Recipe, id=rid, tenant=tenant)
    else:
        recipe = Recipe(tenant=tenant)

    recipe.name = request.POST.get('name', '').strip()
    recipe.portions = int(request.POST.get('portions', '1') or '1')
    recipe.preparation_notes = request.POST.get('preparation_notes', '').strip()
    recipe.save()

    return redirect('settings:recipe_detail', recipe_id=recipe.id)


@require_manager
@require_POST
def recipe_add_ingredient(request, recipe_id):
    tenant = request.user.tenant
    recipe = get_object_or_404(Recipe, id=recipe_id, tenant=tenant)

    item_id = request.POST.get('item_id')
    quantity = Decimal(request.POST.get('quantity', '0') or '0')
    unit_id = request.POST.get('unit_id')
    notes = request.POST.get('notes', '').strip()

    if item_id and quantity > 0 and unit_id:
        RecipeItem.objects.create(
            recipe=recipe,
            item_id=item_id,
            quantity=quantity,
            unit_id=unit_id,
            notes=notes,
        )

    return redirect('settings:recipe_detail', recipe_id=recipe.id)


@require_manager
@require_POST
def recipe_remove_ingredient(request, recipe_id, ingredient_id):
    tenant = request.user.tenant
    recipe = get_object_or_404(Recipe, id=recipe_id, tenant=tenant)
    ingredient = get_object_or_404(RecipeItem, id=ingredient_id, recipe=recipe)
    ingredient.delete()
    return redirect('settings:recipe_detail', recipe_id=recipe.id)


@require_manager
def recipe_api_cost(request, recipe_id):
    """API: คำนวณต้นทุนสูตร (JSON)"""
    tenant = request.user.tenant
    recipe = get_object_or_404(Recipe, id=recipe_id, tenant=tenant)
    cost = recipe.calculate_cost()
    ingredients = []
    for ri in recipe.ingredients.select_related('item', 'unit'):
        ingredients.append({
            'name': ri.item.name,
            'qty': str(ri.quantity),
            'unit': ri.unit.abbreviation,
            'unit_cost': str(ri.item.cost_per_unit),
            'line_cost': str(ri.get_cost()),
        })
    return JsonResponse({
        'cost_per_portion': str(cost),
        'portions': recipe.portions,
        'total_cost': str(cost * recipe.portions),
        'ingredients': ingredients,
    })
