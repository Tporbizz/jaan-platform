"""
สร้าง superuser + tenant + import เมนูจริง สำหรับ production
รันตอน build บน Render อัตโนมัติ
"""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Setup production: create tenant, superuser, import real menu'

    def handle(self, *args, **options):
        from accounts.models import Tenant, User

        # --- Create Tenant ---
        tenant, created = Tenant.objects.get_or_create(
            name='สารข้าว Restaurant',
            defaults={'slug': 'sarakhao'},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created tenant: {tenant.name}'))
        else:
            self.stdout.write(f'Tenant already exists: {tenant.name}')

        # --- Create Superuser ---
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'jaan2024!')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@sarakhao.com')

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_superuser': True,
                'is_staff': True,
                'tenant': tenant,
                'department': 'gm',
                'role': 'owner',
            }
        )
        # Always reset password and ensure tenant
        user.set_password(password)
        user.tenant = tenant
        user.is_superuser = True
        user.is_staff = True
        user.save()
        status = 'Created' if created else 'Reset password for'
        self.stdout.write(self.style.SUCCESS(
            f'{status} superuser: {username} / {password}'
        ))

        # --- Import Real Menu ---
        from restaurant.models import MenuItem
        if MenuItem.objects.filter(tenant=tenant).count() == 0:
            call_command('import_real_menu')
            self.stdout.write(self.style.SUCCESS('Imported 97 real menu items'))
        else:
            self.stdout.write(f'Menu already imported: {MenuItem.objects.filter(tenant=tenant).count()} items')

        # --- Seed Ingredients & Recipes ---
        from restaurant.models import Item
        if Item.objects.filter(tenant=tenant).count() == 0:
            call_command('seed_ingredients')
            self.stdout.write(self.style.SUCCESS('Seeded ingredients and recipes'))
        else:
            self.stdout.write(f'Ingredients already exist: {Item.objects.filter(tenant=tenant).count()} items')

        self.stdout.write(self.style.SUCCESS('Production setup complete!'))
