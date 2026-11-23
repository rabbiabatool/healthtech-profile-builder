"""Regression tests for Issue 2: Policy Persistence and Cross-Worker Index Synchronization.

Demonstrates that:
1. Worker/registry A uploads a policy (starts PENDING).
2. Registry A approves it.
3. Separate registry B sharing the database sees it.
4. Registry B retrieves the approved content.
5. Creating a new registry instance retains all documents.
6. Persisted documents survive registry instantiation / application restart.
7. Replacing a document updates the approved retrieval version correctly.
8. Revoking an approved document immediately removes it from retrieval.
9. Stale retrieval indexes cannot return outdated or revoked content.
"""
import pytest
from rag.engine import (
    DOCS_DIR,
    PolicyRegistry,
    bump_corpus_version,
    get_corpus_version,
    get_store,
    reset_vector_store_cache,
)
from rag.models import PolicyDocumentRecord

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_store_cache():
    reset_vector_store_cache()
    yield
    reset_vector_store_cache()


def test_cross_registry_shared_storage_and_lifecycle():
    """Worker A uploads and approves a document; Worker B immediately sees and retrieves it."""
    # Worker A
    registry_a = PolicyRegistry(docs_dir=DOCS_DIR)
    doc_name = "after_hours_care.txt"
    content = "Greenleaf Clinic provides urgent telephone triage after hours via 555-0199."

    v_initial = get_corpus_version()

    # 1. Worker A uploads
    uploaded = registry_a.upload_document(
        doc_name=doc_name,
        content=content,
        uploaded_by="admin_a@greenleaf.test",
        version="1.0.0",
    )
    assert uploaded.status == "PENDING"

    # Worker B inspects storage: sees PENDING doc
    registry_b = PolicyRegistry(docs_dir=DOCS_DIR)
    all_b = registry_b.list_documents()
    assert any(d["doc_name"] == doc_name and d["status"] == "PENDING" for d in all_b)

    # Retrieval index before approval does NOT contain after_hours_care
    approved_docs_before = registry_b.get_approved_documents()
    assert not any(d.doc_name == doc_name for d in approved_docs_before)

    # 2. Worker A approves it
    approved = registry_a.approve_document(doc_name, approved_by="admin_a@greenleaf.test")
    assert approved.status == "APPROVED"
    assert approved.approved_by == "admin_a@greenleaf.test"

    v_after_approve = get_corpus_version()
    assert v_after_approve > v_initial, "Approving a policy must bump global corpus version!"

    # 3. Worker B sees approved status and retrieves approved content
    approved_docs_b = registry_b.get_approved_documents()
    matching = [d for d in approved_docs_b if d.doc_name == doc_name]
    assert len(matching) == 1
    assert matching[0].content == content

    # 4. Retrieval store synchronized: store retrieves after_hours_care
    store = get_store()
    results = store.retrieve("after hours urgent telephone", top_k=3)
    assert any(r["doc_name"] == doc_name for r in results), f"Expected {doc_name} in retrieval results: {results}"


def test_persisted_documents_survive_registry_restart():
    """Creating a new registry does not lose the document; data is durable in database."""
    doc_name = "durable_check.txt"
    content = "Durable policy content that persists across any process restart."

    reg1 = PolicyRegistry(docs_dir=DOCS_DIR)
    reg1.upload_document(doc_name, content, uploaded_by="admin1@greenleaf.test")
    reg1.approve_document(doc_name, approved_by="admin1@greenleaf.test")

    # Simulate restart by instantiating clean registry instances
    reg2 = PolicyRegistry(docs_dir=DOCS_DIR)
    assert reg2.documents.get(doc_name) is not None
    reg3 = PolicyRegistry(docs_dir=DOCS_DIR)

    doc_in_reg3 = reg3.documents.get(doc_name)
    assert doc_in_reg3 is not None
    assert doc_in_reg3.content == content
    assert doc_in_reg3.status == "APPROVED"


def test_replacing_document_updates_version_and_retrieval():
    """Replacing an existing policy updates the content, sets PENDING, and bumps version on approval."""
    reg = PolicyRegistry(docs_dir=DOCS_DIR)
    doc_name = "lab_hours.txt"

    # Initial version 1.0.0
    reg.upload_document(doc_name, "Lab blood draw hours are 8am to 12pm on weekdays.", uploaded_by="admin@test", version="1.0.0")
    reg.approve_document(doc_name, approved_by="admin@test")
    v1 = get_corpus_version()

    store_v1 = get_store()
    res1 = store_v1.retrieve("blood draw hours", top_k=3)
    assert any("8am to 12pm" in r["text"] for r in res1)

    # Replace with version 2.0.0 (new content: 7am to 4pm)
    reg.replace_document(
        doc_name=doc_name,
        content="Lab blood draw hours have been expanded: 7am to 4pm Monday through Saturday.",
        uploaded_by="admin@test",
        version="2.0.0",
    )
    # Starts PENDING; approved retrieval still returns old or excludes pending
    replaced_record = PolicyDocumentRecord.objects.get(doc_id=doc_name)
    assert replaced_record.status == "PENDING"
    assert replaced_record.version == "2.0.0"

    # Approve replacement
    reg.approve_document(doc_name, approved_by="admin@test")
    v2 = get_corpus_version()
    assert v2 > v1, "Approving replacement must bump corpus version!"

    # New store must reflect updated version and new hours
    store_v2 = get_store()
    res2 = store_v2.retrieve("blood draw hours", top_k=3)
    assert any("7am to 4pm" in r["text"] for r in res2)
    assert not any("8am to 12pm" in r["text"] for r in res2)


def test_revoking_document_removes_from_approved_retrieval():
    """Revoking an approved document immediately bumps version and removes it from retrieval."""
    reg = PolicyRegistry(docs_dir=DOCS_DIR)
    doc_name = "obsolete_covid_policy.txt"
    reg.upload_document(doc_name, "Mandatory mask requirement in all waiting areas.", uploaded_by="admin@test")
    reg.approve_document(doc_name, approved_by="admin@test")

    v_before = get_corpus_version()
    store = get_store()
    res_before = store.retrieve("mandatory mask requirement", top_k=3)
    assert any(r["doc_name"] == doc_name for r in res_before)

    # Revoke
    revoked = reg.revoke_document(doc_name, revoked_by="safety_officer@test")
    assert revoked.status == "REVOKED"
    assert revoked.revoked_by == "safety_officer@test"
    assert revoked.revoked_at is not None

    v_after = get_corpus_version()
    assert v_after > v_before, "Revoking a document must bump corpus version!"

    # Retrieval store must immediately exclude the revoked document
    store_new = get_store()
    res_after = store_new.retrieve("mandatory mask requirement", top_k=5)
    assert not any(r["doc_name"] == doc_name for r in res_after), "Revoked document must NOT appear in retrieval!"


def test_stale_index_rebuilt_across_workers():
    """Demonstrates that a worker holding a stale corpus index rebuilds when DB version changes."""
    reg = PolicyRegistry(docs_dir=DOCS_DIR)
    assert reg is not None
    initial_version = get_corpus_version()
    store = get_store()
    assert store.corpus_version == initial_version

    # Simulate another worker updating the DB and bumping version
    bump_corpus_version()
    new_version = get_corpus_version()
    assert new_version > initial_version

    # Current process get_store() detects version mismatch and supplies synchronized store
    synchronized_store = get_store()
    assert synchronized_store.corpus_version == new_version
