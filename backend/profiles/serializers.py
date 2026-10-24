from django.utils import timezone
from rest_framework import serializers

from .completion import ITEM_LABELS
from .services import completion_for
from .models import Demographics, EmergencyContact, HealthProfile, WellnessPreferences
from .validators import multi_line_text, phone_number, single_line_text


class DemographicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Demographics
        fields = [
            "date_of_birth",
            "gender",
            "blood_group",
            "height_cm",
            "weight_kg",
            "country",
            "preferred_language",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
        extra_kwargs = {
            "country": {"validators": [single_line_text]},
            "preferred_language": {"validators": [single_line_text]},
        }

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


class WellnessSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellnessPreferences
        fields = [
            "contact_preference",
            "wellness_goals",
            "activity_level",
            "diet_preference",
            "sleep_goal_hours",
            "reminder_channel",
            "allergy_notes",
            "condition_notes",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
        extra_kwargs = {
            "wellness_goals": {"max_length": 500, "validators": [multi_line_text]},
            "allergy_notes": {"max_length": 1000, "validators": [multi_line_text]},
            "condition_notes": {"max_length": 1000, "validators": [multi_line_text]},
        }

    def validate_sleep_goal_hours(self, value):
        if value is not None and not (3 <= value <= 14):
            raise serializers.ValidationError("Sleep goal must be between 3 and 14 hours.")
        return value


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            "id",
            "name",
            "relationship",
            "phone",
            "email",
            "is_primary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "name": {"validators": [single_line_text]},
            "phone": {"required": True, "allow_blank": False, "validators": [phone_number]},
        }


def completion_payload(profile):
    result = completion_for(profile)
    return {
        "percent": profile.completion_percent,
        "status": profile.completion_status,
        "missing": [{"key": key, "label": ITEM_LABELS[key]} for key in result.missing],
    }


class MyProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    completion = serializers.SerializerMethodField()
    demographics = DemographicsSerializer(read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    wellness = WellnessSerializer(read_only=True)

    class Meta:
        model = HealthProfile
        fields = [
            "id",
            "full_name",
            "email",
            "status",
            "completion",
            "demographics",
            "emergency_contacts",
            "wellness",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_completion(self, profile):
        return completion_payload(profile)


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
            "status",
            "completion_percent",
            "completion_status",
            "created_at",
        ]
        read_only_fields = fields


class AdminProfileSerializer(MyProfileSerializer):
    user_id = serializers.IntegerField(read_only=True)

    class Meta(MyProfileSerializer.Meta):
        fields = MyProfileSerializer.Meta.fields + ["user_id"]
        read_only_fields = fields