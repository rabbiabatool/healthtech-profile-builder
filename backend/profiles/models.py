from django.conf import settings
from django.db import models


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


class HealthProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    allergies = models.TextField(blank=True)
    conditions = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=ProfileStatus.choices,
        default=ProfileStatus.ACTIVE,
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
                condition=models.Q(height_cm__isnull=True) | models.Q(height_cm__gt=0),
                name="profile_height_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(weight_kg__isnull=True) | models.Q(weight_kg__gt=0),
                name="profile_weight_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ProfileStatus.values),
                name="profile_status_is_valid",
            ),
        ]

    def __str__(self):
        return f"Profile of {self.user_id}"