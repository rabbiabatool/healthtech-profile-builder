from django.conf import settings
from django.db import models
from django.db.models import Q


class BloodGroup(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"


class ProfileStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class CompletionStatus(models.TextChoices):
    NOT_STARTED = "NOT_STARTED", "Not started"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETE = "COMPLETE", "Complete"


class Gender(models.TextChoices):
    FEMALE = "FEMALE", "Female"
    MALE = "MALE", "Male"
    NON_BINARY = "NON_BINARY", "Non-binary"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY", "Prefer not to say"


class ActivityLevel(models.TextChoices):
    SEDENTARY = "SEDENTARY", "Sedentary"
    LIGHT = "LIGHT", "Lightly active"
    MODERATE = "MODERATE", "Moderately active"
    ACTIVE = "ACTIVE", "Very active"


class DietPreference(models.TextChoices):
    NO_PREFERENCE = "NO_PREFERENCE", "No preference"
    VEGETARIAN = "VEGETARIAN", "Vegetarian"
    VEGAN = "VEGAN", "Vegan"
    HALAL = "HALAL", "Halal"
    LOW_SUGAR = "LOW_SUGAR", "Low sugar"
    OTHER = "OTHER", "Other"


class ReminderChannel(models.TextChoices):
    NONE = "NONE", "No reminders"
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "Text message"
    APP = "APP", "In-app"


class Relationship(models.TextChoices):
    PARENT = "PARENT", "Parent"
    SPOUSE = "SPOUSE", "Spouse or partner"
    SIBLING = "SIBLING", "Sibling"
    CHILD = "CHILD", "Child"
    FRIEND = "FRIEND", "Friend"
    OTHER = "OTHER", "Other"


class HealthProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    status = models.CharField(
        max_length=10,
        choices=ProfileStatus.choices,
        default=ProfileStatus.ACTIVE,
    )
    completion_percent = models.PositiveSmallIntegerField(default=0)
    completion_status = models.CharField(
        max_length=12,
        choices=CompletionStatus.choices,
        default=CompletionStatus.NOT_STARTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "health_profiles"
        indexes = [
            models.Index(
                fields=["status", "-created_at", "-id"],
                name="idx_profile_status_created_id",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=ProfileStatus.values),
                name="profile_status_is_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(completion_status="NOT_STARTED", completion_percent=0)
                    | Q(completion_status="IN_PROGRESS", completion_percent__gt=0, completion_percent__lt=100)
                    | Q(completion_status="COMPLETE", completion_percent=100)
                ),
                name="profile_completion_consistent",
            ),
        ]

    def __str__(self):
        return f"Profile of {self.user_id}"
    
class Demographics(models.Model):
    profile = models.OneToOneField(
        HealthProfile,
        on_delete=models.CASCADE,
        related_name="demographics",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    country = models.CharField(max_length=60, blank=True)
    preferred_language = models.CharField(max_length=40, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profile_demographics"
        constraints = [
            models.CheckConstraint(
                condition=Q(height_cm__isnull=True) | Q(height_cm__gte=30, height_cm__lte=272),
                name="demographics_height_in_range",
            ),
            models.CheckConstraint(
                condition=Q(weight_kg__isnull=True) | Q(weight_kg__gte=2, weight_kg__lte=650),
                name="demographics_weight_in_range",
            ),
            models.CheckConstraint(
                condition=Q(gender="") | Q(gender__in=Gender.values),
                name="demographics_gender_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(blood_group="") | Q(blood_group__in=BloodGroup.values),
                name="demographics_blood_group_is_valid",
            ),
        ]

    def __str__(self):
        return f"Demographics of profile {self.profile_id}"


class EmergencyContact(models.Model):
    profile = models.ForeignKey(
        HealthProfile,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    name = models.CharField(max_length=100)
    relationship = models.CharField(
        max_length=10,
        choices=Relationship.choices,
        default=Relationship.OTHER,
    )
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "emergency_contacts"
        ordering = ["-is_primary", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile"],
                condition=Q(is_primary=True),
                name="uniq_primary_contact_per_profile",
            ),
            models.UniqueConstraint(
                fields=["profile", "phone"],
                condition=~Q(phone=""),
                name="uniq_contact_phone_per_profile",
            ),
            models.CheckConstraint(
                condition=~Q(name=""),
                name="contact_name_not_blank",
            ),
            models.CheckConstraint(
                condition=Q(relationship__in=Relationship.values),
                name="contact_relationship_is_valid",
            ),
        ]

    def __str__(self):
        return f"Contact {self.pk} of profile {self.profile_id}"


class WellnessPreferences(models.Model):
    profile = models.OneToOneField(
        HealthProfile,
        on_delete=models.CASCADE,
        related_name="wellness",
    )
    activity_level = models.CharField(max_length=12, choices=ActivityLevel.choices, blank=True)
    diet_preference = models.CharField(max_length=15, choices=DietPreference.choices, blank=True)
    sleep_goal_hours = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    reminder_channel = models.CharField(max_length=10, choices=ReminderChannel.choices, blank=True)
    wellness_goals = models.TextField(blank=True)
    allergy_notes = models.TextField(blank=True)
    condition_notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wellness_preferences"
        constraints = [
            models.CheckConstraint(
                condition=Q(sleep_goal_hours__isnull=True) | Q(sleep_goal_hours__gte=3, sleep_goal_hours__lte=14),
                name="wellness_sleep_goal_in_range",
            ),
            models.CheckConstraint(
                condition=Q(activity_level="") | Q(activity_level__in=ActivityLevel.values),
                name="wellness_activity_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(diet_preference="") | Q(diet_preference__in=DietPreference.values),
                name="wellness_diet_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(reminder_channel="") | Q(reminder_channel__in=ReminderChannel.values),
                name="wellness_reminder_is_valid",
            ),
        ]

    def __str__(self):
        return f"Wellness preferences of profile {self.profile_id}"