from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "phone")
        read_only_fields = ("id", "role")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Parolni tasdiqlash")

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "phone", "password", "password2",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Parollar mos kelmadi."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
