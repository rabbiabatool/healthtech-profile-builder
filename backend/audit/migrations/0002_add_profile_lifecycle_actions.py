from django.db import migrations, models
from django.db.models import Q


def _action_values():
    """Return all AuditAction values including the two new lifecycle events."""
    return [
        "DEMOGRAPHICS_UPDATED",
        "DEMOGRAPHICS_RESET",
        "WELLNESS_UPDATED",
        "WELLNESS_RESET",
        "EMERGENCY_CONTACT_CREATED",
        "EMERGENCY_CONTACT_UPDATED",
        "EMERGENCY_CONTACT_DELETED",
        "ADMIN_LOGIN",
        "ADMIN_LOGIN_FAILED",
        "ADMIN_LOGOUT",
        "ADMIN_PROFILE_VIEWED",
        "ADMIN_SEARCH_PERFORMED",
        "ADMIN_PROFILE_DEACTIVATED",
        "ADMIN_PROFILE_REACTIVATED",
        "PROFILE_CREATED",
        "PROFILE_DELETED",
    ]


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        # Drop the old constraint, recreate it with the two new action values.
        migrations.RemoveConstraint(
            model_name="auditevent",
            name="audit_action_is_valid",
        ),
        migrations.AddConstraint(
            model_name="auditevent",
            constraint=models.CheckConstraint(
                condition=Q(action__in=_action_values()),
                name="audit_action_is_valid",
            ),
        ),
    ]

