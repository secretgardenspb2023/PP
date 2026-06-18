"""Auth serializers (ТЗ Этап 3)."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    # full_name is a property over first_name/last_name — declare it explicitly.
    full_name = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = User
        fields = ["email", "full_name", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        # Inactive until the email is confirmed (ТЗ 3.3).
        return User.objects.create_user(password=password, is_active=False, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class EmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=12)


class ResendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    social_provider = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "is_active", "is_staff", "date_joined",
            "social_provider",
        ]
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.Serializer):
    """Editable profile fields (ТЗ 3.11). Email/login are identity — not editable here."""

    full_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def update(self, instance, validated_data):
        if "full_name" in validated_data:
            instance.full_name = validated_data["full_name"]
        if "phone" in validated_data:
            instance.phone = validated_data["phone"] or None
        instance.save()
        return instance
