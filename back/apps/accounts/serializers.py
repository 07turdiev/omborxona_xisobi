from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Xodim. Parol bu yerda ko'rinmaydi va shu yerda o'zgarmaydi."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'role_display', 'is_active', 'last_login',
        )
        read_only_fields = ('id', 'last_login')

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username


class UserCreateSerializer(UserSerializer):
    """Yangi xodim: parol majburiy va Django qoidalaridan o'tadi."""

    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta(UserSerializer.Meta):
        fields = (*UserSerializer.Meta.fields, 'password')

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user


class SetPasswordSerializer(serializers.Serializer):
    """Administrator xodimga yangi parol qo'yadi."""

    password = serializers.CharField(style={'input_type': 'password'})

    def validate_password(self, value):
        validate_password(value)
        return value
