from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)
    branch_name = serializers.CharField(source='restaurant_branch.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'avatar',
            'tenant', 'tenant_name',
            'restaurant_branch', 'branch_name',
        ]
        read_only_fields = ['id', 'tenant']
