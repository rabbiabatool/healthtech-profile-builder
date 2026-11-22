from django.db import models


class PolicyDocumentRecord(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REVOKED", "Revoked"),
    ]

    doc_id = models.CharField(max_length=120, unique=True, db_index=True)
    doc_name = models.CharField(max_length=255, db_index=True)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    version = models.CharField(max_length=50, default="1.0.0")
    metadata = models.JSONField(default=dict, blank=True)
    uploaded_by = models.CharField(max_length=255, default="system")
    approved_by = models.CharField(max_length=255, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.CharField(max_length=255, null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rag_policy_documents"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.doc_name} ({self.status} v{self.version})"


class PolicyCorpusState(models.Model):
    """Tracks global approved corpus version across all workers."""
    version = models.PositiveBigIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rag_corpus_state"

    def __str__(self):
        return f"CorpusVersion({self.version})"
