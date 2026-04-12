"""
Import real menu data from Sarakao Restaurant website.
Usage: python manage.py import_real_menu
"""
from django.core.management.base import BaseCommand

from accounts.models import Tenant
from restaurant.models import MenuItem


# =========================================================================
# Complete menu data from Sarakao Restaurant
# =========================================================================

FOOD_MENUS = [
    # === แกง (soup) ===
    ('soup', 'แกงคั่วไก่ใบรา', 'Curry with chicken and basil', 200, 'kitchen', 15),
    ('soup', 'ไก่หลุมกะทิโรตี', 'Coconut milk chicken with roti', 250, 'kitchen', 20),
    ('soup', 'แกงส้มปลากะพง', 'Southern Thai spicy sour yellow curry with seabass', 250, 'kitchen', 15),
    ('soup', 'แกงคั่วกระดูกอ่อนหมู', 'Southern Thai curry with spareribs', 280, 'kitchen', 20),
    ('soup', 'แกงคั่วปูใบชะพลู', 'Crab meat in southern coconut curry with betel leaf', 280, 'kitchen', 20),

    # === ผัด (stir_fry) ===
    ('stir_fry', 'ผัดผักหวาน', 'Stir fried sweet leaf', 160, 'kitchen', 8),
    ('stir_fry', 'หมูบะเตง', 'Pork bateng', 180, 'kitchen', 10),
    ('stir_fry', 'ผักเหมียงคั่วไข่', 'Stir fried melinjo leaves with egg', 180, 'kitchen', 8),
    ('stir_fry', 'เอ็นไก่คั่วรีปลี', 'Stir fried chicken tendons with chili', 200, 'kitchen', 12),
    ('stir_fry', 'กุ้งผัดพริกเกลือ', 'Stir fried shrimp with chili and salt', 220, 'kitchen', 10),
    ('stir_fry', 'กุ้งใหญ่ผัดกุ้งเล็ก', 'Stir fried shrimp with shrimp paste', 220, 'kitchen', 10),
    ('stir_fry', 'ปลากะพงผัดเครื่องแกง', 'Stir fried seabass with curry paste', 250, 'kitchen', 12),
    ('stir_fry', 'คั่วกลิ้งหมูสับ', 'Southern dry curry with minced pork', 250, 'kitchen', 12),
    ('stir_fry', 'ผัดเผ็ดหมูสามชั้นลูกตอ', 'Stir fried pork belly with sator', 280, 'kitchen', 12),
    ('stir_fry', 'หมูผัดเคยลูกตอ', 'Stir fried pork with shrimp paste and sator', 280, 'kitchen', 12),

    # === ต้ม (boil) ===
    ('boil', 'ต้มข่าไก่', 'Tom kha gai', 180, 'kitchen', 15),
    ('boil', 'ต้มเปรตไก่', 'Boiled chicken with turmeric', 180, 'kitchen', 15),
    ('boil', 'ต้มยำซีฟู้ด/กุ้ง', 'Seafood or prawn Tom Yum', 180, 'kitchen', 12),
    ('boil', 'ฮ้องหมูย่าง', 'Hong moo roast', 240, 'kitchen', 25),
    ('boil', 'ต้มข่าคาปู', 'Tom kha crab', 240, 'kitchen', 15),
    ('boil', 'ต้มกะทิผักเหมียงกุ้งสด', 'Coconut milk soup with melinjo and fresh shrimp', 280, 'kitchen', 15),
    ('boil', 'ต้มจืดสาหร่ายเต้าหู้หมูสับ', 'Clear soup with seaweed, tofu and minced pork', 280, 'kitchen', 15),

    # === ทอด (deep_fry) ===
    ('deep_fry', 'หมูทอดกระเทียม', 'Deep fried pork with garlic', 180, 'kitchen', 12),
    ('deep_fry', 'ปีกไก่ทอดน้ำปลา', 'Deep fried chicken wings with fish sauce', 180, 'kitchen', 12),
    ('deep_fry', 'ไข่เจียวฟูขมิ้นกรอบ', 'Thai omelette with minced pork', 200, 'kitchen', 8),
    ('deep_fry', 'เอ็นข้อไก่ทอด', 'Fried chicken tendons', 200, 'kitchen', 12),
    ('deep_fry', 'ปลาพงทอดน้ำปลา', 'Deep fried seabass with fish sauce', 250, 'kitchen', 15),
    ('deep_fry', 'ปลากะพงทอดขมิ้น', 'Deep fried seabass with turmeric', 250, 'kitchen', 15),
    ('deep_fry', 'ปลาอินทรีย์ทอดน้ำปลา', 'Deep fried mackerel with fish sauce', 280, 'kitchen', 15),

    # === ชุดน้ำพริก (chili_paste) ===
    ('chili_paste', 'น้ำชุบหยำ', 'Southern chili paste', 160, 'kitchen', 10),
    ('chili_paste', 'น้ำพริกมะกรูด', 'Kaffir lime chili paste', 160, 'kitchen', 10),

    # === ยำ (salad) ===
    ('salad', 'ยำทะเลตรัง', 'Spicy seafood salad Trang style', 220, 'kitchen', 10),
    ('salad', 'ยำเอ็นข้อไก่', 'Spicy chicken tendon salad', 200, 'kitchen', 10),
    ('salad', 'พล่าปลากระพง', 'Spicy seabass salad', 250, 'kitchen', 10),

    # === สเต๊ก (steak) ===
    ('steak', 'สเต๊กปลากะพงซอสต้มยำ', 'Seabass steak with Tom Yum sauce', 320, 'kitchen', 18),
    ('steak', 'สเต๊กปลาแซลมอนวาซาบิซอส', 'Salmon steak with wasabi sauce', 350, 'kitchen', 18),

    # === อาหารจานเดียว (single_dish) ===
    ('single_dish', 'คั่วไก่/คั่วหมู', 'Kuamoo / Kuagai', 160, 'kitchen', 10),
    ('single_dish', 'ข้าวไข่เยิ้มกะเพราหมูสับ', 'Rice with basil minced pork and runny egg', 160, 'kitchen', 8),
    ('single_dish', 'ข้าวไข่ข้นแกงคั่วกระดูกอ่อนหมู', 'Southern curry rice with spareribs', 180, 'kitchen', 10),
    ('single_dish', 'ข้าวราดเครื่องแกงปลาพง/ซีฟู้ด', 'Rice with curry seabass/seafood', 180, 'kitchen', 10),
    ('single_dish', 'ข้าวผัดต้มยำซีฟู้ด', 'Tom Yum seafood fried rice', 180, 'kitchen', 10),
    ('single_dish', 'ข้าวหน้าแซลมอนไข่ดองซีอิ๊ว', 'Salmon rice bowl with marinated egg', 280, 'kitchen', 12),

    # === พาสต้า (pasta) ===
    ('pasta', 'พาสต้าโบโลเนสหมู', 'Pasta pork bolognese', 180, 'kitchen', 12),
    ('pasta', 'พาสต้าคาโบนาร่า', 'Pasta carbonara', 200, 'kitchen', 12),
    ('pasta', 'พาสต้าเบค่อนพริกแห้ง', 'Pasta bacon with dried chili', 200, 'kitchen', 12),
    ('pasta', 'พาสต้าหมูฮ้อง', 'Pasta moo hong', 250, 'kitchen', 15),

    # === อาหารทานเล่น (snack) ===
    ('snack', 'หัวครกอบเกลือ', 'Hua krok baked with salt', 100, 'kitchen', 8),
    ('snack', 'มันฝรั่งทอด (รสชีส/รสบาบีคิว)', 'French fries (cheese/BBQ flavor)', 120, 'kitchen', 8),
    ('snack', 'นักเกตไก่และมันฝรั่งทอด', 'Chicken nuggets and French fries', 160, 'kitchen', 10),

    # === ของหวาน (dessert) ===
    ('dessert', 'บราวนี่ช้อต', 'Brownies shot', 180, 'kitchen', 10),
    ('dessert', 'โรตีกรอบ', 'Crispy roti', 180, 'kitchen', 8),
    ('dessert', 'วาฟเฟิลสังขยาเมืองตรัง', 'Coconut waffle Trang style', 200, 'kitchen', 10),
]

DRINK_MENUS = [
    # === Signature Cocktails ===
    ('cocktail', 'Gin Tropical', 'Signature cocktail', 225, 'bar', 5),
    ('cocktail', 'Late Night Lychee', 'Signature cocktail', 225, 'bar', 5),
    ('cocktail', 'Roasted Pork Rhapsody', 'Signature cocktail', 225, 'bar', 5),

    # === Cocktails ===
    ('cocktail', 'Green Refreshing', 'Cocktail', 220, 'bar', 5),
    ('cocktail', 'Parima Fruit Punch', 'Cocktail', 220, 'bar', 5),
    ('cocktail', 'Parima Splash', 'Cocktail', 220, 'bar', 5),
    ('cocktail', 'So Proud', 'Cocktail', 220, 'bar', 5),
    ('cocktail', 'Long Island Iced Tea', 'Cocktail', 220, 'bar', 5),
    ('cocktail', 'Margarita', 'Cocktail', 220, 'bar', 5),
    ('cocktail', 'Mai Tai', 'Cocktail', 220, 'bar', 5),
    ('cocktail', 'Pina Colada', 'Cocktail', 220, 'bar', 5),

    # === Mocktails ===
    ('mocktail', 'Parima Virgin Fruit Punch', 'Mocktail', 135, 'bar', 5),
    ('mocktail', 'Parima Virgin Mojito', 'Mocktail', 135, 'bar', 5),
    ('mocktail', 'Virgin Pina Colada', 'Mocktail', 120, 'bar', 5),

    # === Signature Mocktails ===
    ('mocktail', 'Sangria', 'Signature mocktail', 160, 'bar', 5),
    ('mocktail', 'Pinky Sour', 'Signature mocktail', 135, 'bar', 5),
    ('mocktail', 'Simple', 'Signature mocktail', 135, 'bar', 5),
    ('mocktail', 'Green Leaf Shake', 'Signature mocktail', 135, 'bar', 5),

    # === Smoothie / Shake ===
    ('smoothie', 'Tropicana Smoothie', 'Smoothie', 120, 'bar', 3),
    ('smoothie', 'Strawberry Smoothie', 'Smoothie', 120, 'bar', 3),
    ('smoothie', 'Blueberry Smoothie', 'Smoothie', 120, 'bar', 3),
    ('smoothie', 'Banana Milk Shake', 'Milk shake', 120, 'bar', 3),

    # === Fruit Shake ===
    ('smoothie', 'Watermelon Shake', 'Fruit shake', 120, 'bar', 3),
    ('smoothie', 'Lime Shake', 'Fruit shake', 120, 'bar', 3),
    ('smoothie', 'Pineapple Shake', 'Fruit shake', 120, 'bar', 3),

    # === Coffee & Tea ===
    ('coffee', 'Americano', 'Hot/Iced', 100, 'bar', 3),
    ('coffee', 'Espresso', 'Hot/Iced', 100, 'bar', 3),
    ('coffee', 'Latte', 'Hot/Iced', 100, 'bar', 3),
    ('coffee', 'Cappuccino', 'Hot/Iced', 100, 'bar', 3),
    ('coffee', 'Cocoa', 'Hot/Iced', 100, 'bar', 3),
    ('coffee', 'Lemon Tea', 'Hot/Iced', 100, 'bar', 3),
    ('coffee', 'Mocha', 'Hot/Iced', 100, 'bar', 3),
    ('coffee', 'Thai Coffee', 'Hot/Iced', 100, 'bar', 3),

    # === Beer ===
    ('beer', 'Hoegaarden Rosee', 'Beer', 180, 'bar', 1),
    ('beer', 'Heineken', 'Beer', 140, 'bar', 1),
    ('beer', 'Chang', 'Beer', 120, 'bar', 1),
    ('beer', 'Singha', 'Beer', 120, 'bar', 1),
    ('beer', 'Leo', 'Beer', 120, 'bar', 1),

    # === Soft Drink ===
    ('soft_drink', 'Mineral Water', 'Soft drink', 40, 'bar', 1),
    ('soft_drink', 'Coke', 'Soft drink', 40, 'bar', 1),
    ('soft_drink', 'Coke Light', 'Soft drink', 40, 'bar', 1),
    ('soft_drink', 'Sprite', 'Soft drink', 40, 'bar', 1),
    ('soft_drink', 'Soda', 'Soft drink', 40, 'bar', 1),
    ('soft_drink', 'Ginger Ale', 'Soft drink', 40, 'bar', 1),
    ('soft_drink', 'Tonic Water', 'Soft drink', 40, 'bar', 1),
]


class Command(BaseCommand):
    help = 'Import real Sarakao restaurant menu'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing menu items first')

    def handle(self, *args, **options):
        tenant = Tenant.objects.first()
        if not tenant:
            self.stderr.write('No tenant found!')
            return

        if options['clear']:
            deleted = MenuItem.objects.filter(tenant=tenant).delete()
            self.stdout.write(f'Cleared {deleted[0]} existing menu items')

        all_menus = FOOD_MENUS + DRINK_MENUS
        created = 0
        updated = 0

        for i, (cat, name, name_en, price, station, prep_time) in enumerate(all_menus):
            obj, is_new = MenuItem.objects.update_or_create(
                tenant=tenant,
                name=name,
                defaults={
                    'name_en': name_en,
                    'menu_category': cat,
                    'selling_price': price,
                    'prep_station': station,
                    'prep_time_minutes': prep_time,
                    'is_available': True,
                    'sort_order': i,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done! Created: {created}, Updated: {updated}, Total: {len(all_menus)}'
        ))

        # Summary by category
        from django.db.models import Count
        cats = MenuItem.objects.filter(tenant=tenant).values('menu_category').annotate(
            count=Count('id'),
        ).order_by('menu_category')
        self.stdout.write('\nMenu breakdown:')
        for c in cats:
            self.stdout.write(f"  {c['menu_category']}: {c['count']}")
