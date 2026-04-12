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

        if not User.objects.filter(username=username).exists():
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                tenant=tenant,
                department='gm',
                role='owner',
            )
            self.stdout.write(self.style.SUCCESS(
                f'Created superuser: {username} (password: {password})'
            ))
        else:
            # Update existing user's tenant if needed
            user = User.objects.get(username=username)
            if not user.tenant:
                user.tenant = tenant
                user.save()
            self.stdout.write(f'Superuser already exists: {username}')

        # --- Import Real Menu ---
        from restaurant.models import MenuItem
        if MenuItem.objects.filter(tenant=tenant).count() == 0:
            call_command('import_real_menu')
            self.stdout.write(self.style.SUCCESS('Imported 97 real menu items'))
        else:
            self.stdout.write(f'Menu already imported: {MenuItem.objects.filter(tenant=tenant).count()} items')

        self.stdout.write(self.style.SUCCESS('Production setup complete!'))
