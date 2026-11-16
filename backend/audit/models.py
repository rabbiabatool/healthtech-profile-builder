from django.conf import settings
from django.db import models
from django.db.models import Q

TIMELINE_INDEX_NAME = "idx_audit_profile_newest"
ACTION_INDEX_NAME = "idx_audit_action_newest"


class AuditImmutableError(Exception):
    """Raised when code tries to change or delete an audit event."""


class AuditAction(models.TextChoices):
    DEMOGRAPHICS_UPDATED = "DEMOGRAPHICS_UPDATED", "Demographics updated"
    DEMOGRAPHICS_RESET = "DEMOGRAPHICS_RESET", "Demographics reset"
    WELLNESS_UPDATED = "WELLNESS_UPDATED", "Wellness preferences updated"
    WELLNESS_RESET = "WELLNESS_RESET", "Wellness preferences reset"
    EMERGENCY_CONTACT_CREATED = "EMERGENCY_CONTACT_CREATED", "Emergency contact added"
    EMERGENCY_CONTACT_UPDATED = "EMERGENCY_CONTACT_UPDATED", "Emergency contact updated"
    EMERGENCY_CONTACT_DELETED = "EMERGENCY_CONTACT_DELETED", "Emergency contact deleted"
    ADMIN_LOGIN = "ADMIN_LOGIN", "Admin signed in"
    ADMIN_LOGIN_FAILED = "ADMIN_LOGIN_FAILED", "Admin sign-in failed"
    ADMIN_LOGOUT = "ADMIN_LOGOUT", "Admin signed out"
    ADMIN_PROFILE_VIEWED = "ADMIN_PROFILE_VIEWED", "Profile viewed by admin"
    ADMIN_SEARCH_PERFORMED = "ADMIN_SEARCH_PERFORMED", "Profile search performed"
    ADMIN_PROFILE_DEACTIVATED = "ADMIN_PROFILE_DEACTIVATED", "Profile deactivated"
    ADMIN_PROFILE_REACTIVATED = "ADMIN_PROFILE_REACTIVATED", "Profile reactivated"


class ActorRole(models.TextChoices):
    USER = "USER", "Member"
    ADMIN = "ADMIN", "Administrator"
    ANONYMOUS = "ANONYMOUS", "Not signed in"


class Outcome(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class AuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditImmutableError("Audit events cannot be changed.")

    def delete(self):
        raise AuditImmutableError("Audit events cannot be deleted.")


class AuditEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    actor_role = models.CharField(max_length=10, choices=ActorRole.choices)
    action = models.CharField(max_length=40, choices=AuditAction.choices)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.SUCCESS)
    profile_id = models.BigIntegerField(null=True, blank=True)
    changed_fields = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = AuditQuerySet.as_manager()

    class Meta:
        db_table = "audit_events"
        indexes = [
            models.Index(fields=["profile_id", "-id"], name=TIMELINE_INDEX_NAME),
            models.Index(fields=["action", "-id"], name=ACTION_INDEX_NAME),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(action__in=AuditAction.values), name="audit_action_is_valid"),
            models.CheckConstraint(condition=Q(actor_role__in=ActorRole.values), name="audit_actor_role_is_valid"),
            models.CheckConstraint(condition=Q(outcome__in=Outcome.values), name="audit_outcome_is_valid"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditImmutableError("Audit events cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutableError("Audit events cannot be deleted.")

    def __str__(self):
        return f"{self.action} #{self.pk}"
