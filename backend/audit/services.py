from profiles.models import ProfileStatus

from .models import ActorRole, AuditAction, AuditEvent, Outcome

AUDITABLE_FIELDS = frozenset(
    {
        "date_of_birth",
        "gender",
        "blood_group",
        "height_cm",
        "weight_kg",
        "country",
        "preferred_language",
        "activity_level",
        "diet_preference",
        "sleep_goal_hours",
        "reminder_channel",
        "contact_preference",
        "wellness_goals",
        "allergy_notes",
        "condition_notes",
        "name",
        "relationship",
        "phone",
        "email",
        "is_primary",
    }
)
SECTIONS = frozenset({"demographics", "wellness", "emergency_contacts"})
FILTER_NAMES = ("search", "status", "completion_status", "created_after", "created_before")
STATUSES = frozenset(ProfileStatus.values)


def _is_allowed(value, allowed):
    return isinstance(value, str) and value in allowed


def _is_whole_number(value, minimum):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


METADATA_RULES = {
    "section": lambda value: _is_allowed(value, SECTIONS),
    "from_status": lambda value: _is_allowed(value, STATUSES),
    "to_status": lambda value: _is_allowed(value, STATUSES),
    "filters_used": lambda value: isinstance(value, list)
    and all(_is_allowed(item, FILTER_NAMES) for item in value),
    "result_count": lambda value: _is_whole_number(value, 0),
    "contact_id": lambda value: _is_whole_number(value, 1),
}


def _clean_changed_fields(names):
    if isinstance(names, (str, bytes, dict)):
        raise TypeError("changed_fields must be a list of field names.")
    cleaned = set()
    for name in names:
        if not _is_allowed(name, AUDITABLE_FIELDS):
            raise ValueError("Unknown field name for an audit event.")
        cleaned.add(name)
    return sorted(cleaned)


def _clean_metadata(metadata):
    cleaned = {}
    for key, value in (metadata or {}).items():
        rule = METADATA_RULES.get(key)
        if rule is None or not rule(value):
            raise ValueError("Metadata key or value is not allowed in an audit event.")
        cleaned[key] = value
    return cleaned


def record_event(
    actor,
    action,
    *,
    outcome=Outcome.SUCCESS,
    profile_id=None,
    changed_fields=(),
    metadata=None,
):
    if action not in AuditAction.values:
        raise ValueError("Unknown audit action.")
    if outcome not in Outcome.values:
        raise ValueError("Unknown audit outcome.")
    if profile_id is not None and not _is_whole_number(profile_id, 1):
        raise ValueError("Profile id must be a positive whole number.")

    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    role = ActorRole.ANONYMOUS if actor is None else actor.role

    return AuditEvent.objects.create(
        actor=actor,
        actor_role=role,
        action=action,
        outcome=outcome,
        profile_id=profile_id,
        changed_fields=_clean_changed_fields(changed_fields),
        metadata=_clean_metadata(metadata),
    )