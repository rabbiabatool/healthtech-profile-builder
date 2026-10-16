from django.utils import timezone
from rest_framework import serializers

from .models import HealthProfile


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = HealthProfile
        fields = [
            "id",
            "full_name",
            "email",
            "date_of_birth",
            "blood_group",
            "height_cm",
            "weight_kg",
            "allergies",
            "conditions",
            "emergency_contact",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthProfile
        fields = [
            "date_of_birth",
            "blood_group",
            "height_cm",
            "weight_kg",
            "allergies",
            "conditions",
            "emergency_contact",
        ]

    def validate_date_of_birth(self, value):
        if value is not None:
            if value > timezone.localdate():
                raise serializers.ValidationError("Date of birth cannot be in the future.")
            if value.year < 1900:
                raise serializers.ValidationError("Date of birth is not realistic.")
        return value

    def validate_height_cm(self, value):
        if value is not None and not (30 <= value <= 272):
            raise serializers.ValidationError("Height must be between 30 and 272 cm.")
        return value

    def validate_weight_kg(self, value):
        if value is not None and not (2 <= value <= 650):
            raise serializers.ValidationError("Weight must be between 2 and 650 kg.")
        return value

class AdminProfileListSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = HealthProfile
        fields = [
            "id",
            "user_id",
            "full_name",
            "email",
            "blood_group",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class AdminProfileSerializer(ProfileSerializer):
    user_id = serializers.IntegerField(read_only=True)

    class Meta(ProfileSerializer.Meta):
        fields = ProfileSerializer.Meta.fields + ["user_id"]