from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "created_at",
            "actor_id",
            "actor_role",
            "action",
            "outcome",
            "profile_id",
            "changed_fields",
            "metadata",
        ]
        read_only_fields = fields