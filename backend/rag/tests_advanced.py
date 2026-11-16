"""Tests for Week 5 Phase 1: Advanced RAG, Hybrid Retrieval, Versioning, and 20-Question Evaluation Benchmark."""
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate
from types import SimpleNamespace

from rag.advanced_engine import (
    DocumentMetadata,
    PolicyDocument,
    BM25Index,
    AdvancedHybridVectorStore,
    get_advanced_store,
    run_chunk_size_experiment,
)
from rag.advanced_evaluation import (
    EVALUATION_20_DATASET,
    run_comparative_rag_benchmark,
)
from rag.views import (
    AdvancedRAGSearchView,
    AdvancedRAGEval20View,
    DocumentManagementView,
)


# ─── Unit Tests: BM25 Lexical Index ──────────────────────────────────────────

def test_bm25_index_scoring():
    corpus = [
        "Specialist appointments require at least 48 hours notice to cancel without fee.",
        "General practitioner consultations can be cancelled up to 24 hours in advance.",
        "Emergency department visits do not require any booking or cancellation.",
    ]
    bm25 = BM25Index(corpus)
    scores = bm25.get_scores("specialist 48 hours notice")
    assert len(scores) == 3
    # First doc has the exact terms, should have highest score
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_bm25_empty_query():
    corpus = ["First document text", "Second document text"]
    bm25 = BM25Index(corpus)
    scores = bm25.get_scores("")
    assert all(s == 0.0 for s in scores)


# ─── Unit Tests: Document Versioning & Mutations ─────────────────────────────

def test_document_metadata_and_versioning():
    doc = PolicyDocument(
        doc_id="test_doc",
        doc_name="test_telehealth.txt",
        version="1.0.0",
        content="Telehealth video calls require a high-speed stable internet connection.",
        metadata=DocumentMetadata(
            category="clinical",
            department="Telehealth",
            target_audience="patient",
            effective_date="2026-01-01",
        ),
    )
    assert doc.doc_id == "test_doc"
    assert doc.metadata.version if hasattr(doc.metadata, "version") else doc.version == "1.0.0"
    assert len(doc.sha256) == 64
    assert doc.is_active is True


def test_advanced_store_dynamic_lifecycle():
    store = AdvancedHybridVectorStore()

    # 1. Add document
    doc = PolicyDocument(
        doc_id="billing_policy_v1",
        doc_name="billing_policy.txt",
        version="1.0.0",
        content="Co-pay is due at the time of service. Accepted methods include credit card and HSA.",
        metadata=DocumentMetadata(
            category="billing",
            department="Finance",
            target_audience="all",
            effective_date="2026-01-01",
        ),
    )
    store.add_document(doc)
    assert "billing_policy_v1" in store.documents
    assert len(store.chunks) > 0

    # Retrieve before update
    res = store.retrieve_hybrid("What are accepted payment methods for co-pay?", top_k=2)
    assert len(res) > 0
    assert "billing_policy_v1" in res[0]["doc_id"]

    # 2. Update document
    store.update_document(
        doc_id="billing_policy_v1",
        content="Co-pay is waived for preventative screening visits under the 2026 wellness initiative.",
        version="1.1.0",
    )
    assert store.documents["billing_policy_v1"].version == "1.1.0"

    # Check update retrieval
    res_updated = store.retrieve_hybrid("preventative screening wellness waiver", top_k=2)
    assert len(res_updated) > 0
    assert "waived" in res_updated[0]["text"]

    # 3. Soft delete
    store.delete_document("billing_policy_v1", soft=True)
    assert store.documents["billing_policy_v1"].is_active is False
    res_deleted = store.retrieve_hybrid("preventative screening wellness waiver", top_k=2)
    assert not any(r["doc_id"] == "billing_policy_v1" for r in res_deleted)

    # 4. Hard delete
    store.delete_document("billing_policy_v1", soft=False)
    assert "billing_policy_v1" not in store.documents


# ─── Unit Tests: Metadata Filtering ──────────────────────────────────────────

def test_metadata_filtering():
    store = get_advanced_store()

    # Filter by category = 'booking'
    results_booking = store.retrieve_hybrid("appointments and scheduling", filter_metadata={"category": "booking"}, top_k=5)
    for r in results_booking:
        assert r["metadata"]["category"] == "booking"

    # Filter by category = 'privacy'
    results_privacy = store.retrieve_hybrid("data privacy retention", filter_metadata={"category": "privacy"}, top_k=5)
    for r in results_privacy:
        assert r["metadata"]["category"] == "privacy"

    # Filter with non-matching department should return empty
    results_empty = store.retrieve_hybrid("booking appointments", filter_metadata={"department": "NonExistentDept"}, top_k=5)
    assert len(results_empty) == 0


# ─── Unit Tests: Chunk-Size Comparison Experiment ────────────────────────────

def test_chunk_size_experiment():
    queries = [
        "How far in advance can I book an appointment?",
        "What is the cancellation window for specialists?",
        "How long are medical records kept?",
    ]
    exp = run_chunk_size_experiment(sample_queries=queries)
    assert "configurations_tested" in exp
    assert "selected_default" in exp
    assert len(exp["configurations_tested"]) == 3
    for cfg in exp["configurations_tested"]:
        assert cfg["hit_rate_pct"] == 100.0
        assert cfg["total_chunks_indexed"] > 0


# ─── Unit Tests: 20-Question Retrieval Benchmark ─────────────────────────────

def test_benchmark_20_questions_structure():
    assert len(EVALUATION_20_DATASET) == 20
    # Must have 10 answerable, 4 ambiguous, 4 out-of-scope, 2 safety
    categories = [q["category"] for q in EVALUATION_20_DATASET]
    assert categories.count("answerable") == 10
    assert categories.count("ambiguous") == 4
    assert categories.count("out_of_scope") == 4
    assert categories.count("safety_medical") == 1
    assert categories.count("safety_injection") == 1


def test_comparative_benchmark_execution():
    store = get_advanced_store()
    comp = run_comparative_rag_benchmark(store)

    assert "baseline" in comp
    assert "advanced_hybrid" in comp
    assert "improvement_delta" in comp

    adv = comp["advanced_hybrid"]
    assert adv["recall_at_1_pct"] >= 80.0
    assert adv["recall_at_3_pct"] >= 90.0
    assert adv["hit_rate_top3_pct"] >= 90.0
    # Advanced hybrid should have strong abstention on out-of-scope / adversarial
    assert adv["abstention_accuracy_pct"] >= 80.0


# ─── Integration / API Tests ─────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIRequestFactory()


@pytest.fixture
def admin_user():
    return SimpleNamespace(is_authenticated=True, is_active=True, role="ADMIN", email="admin@healthtech.test", id=1)


@pytest.fixture
def member_user():
    return SimpleNamespace(is_authenticated=True, is_active=True, role="USER", email="patient@healthtech.test", id=2)


def test_api_advanced_rag_search(api_client, member_user):
    factory = api_client
    view = AdvancedRAGSearchView.as_view()

    # Search with hybrid retrieval
    request = factory.post(
        "/api/v1/llm/rag/search/",
        data={"query": "How do I cancel a specialist appointment?", "top_k": 3},
        format="json",
    )
    force_authenticate(request, user=member_user)
    response = view(request)
    assert response.status_code == 200
    data = response.data
    assert data["query"] == "How do I cancel a specialist appointment?"
    assert len(data["passages"]) > 0
    assert "cancellation" in data["passages"][0]["doc_name"]


def test_api_advanced_rag_search_with_metadata_filter(api_client, member_user):
    factory = api_client
    view = AdvancedRAGSearchView.as_view()

    request = factory.post(
        "/api/v1/llm/rag/search/",
        data={"query": "data privacy and retention", "filter_metadata": {"category": "privacy"}, "top_k": 3},
        format="json",
    )
    force_authenticate(request, user=member_user)
    response = view(request)
    assert response.status_code == 200
    for res in response.data["passages"]:
        assert res["metadata"]["category"] == "privacy"


def test_api_eval_20_benchmark(api_client, admin_user):
    factory = api_client
    view = AdvancedRAGEval20View.as_view()

    request = factory.get("/api/v1/llm/rag/eval-20/")
    force_authenticate(request, user=admin_user)
    response = view(request)
    assert response.status_code == 200
    data = response.data
    assert "baseline" in data
    assert "advanced_hybrid" in data
    assert "chunk_size_experiment" in data
    assert data["advanced_hybrid"]["total_questions"] == 20
    assert data["advanced_hybrid"]["abstention_accuracy_pct"] >= 80.0


def test_api_document_management_rbac_and_crud(api_client, member_user, admin_user):
    factory = api_client
    view = DocumentManagementView.as_view()

    # Member user must be rejected with 403 Forbidden
    payload = {
        "action": "add",
        "doc_id": "test_unauth_doc",
        "doc_name": "unauthorized.txt",
        "content": "This should not be allowed for non-admin",
        "metadata": {
            "category": "general",
            "department": "general",
            "target_audience": "all",
            "effective_date": "2026-01-01",
        },
    }
    req_member = factory.post("/api/v1/llm/rag/documents/", data=payload, format="json")
    force_authenticate(req_member, user=member_user)
    resp_member = view(req_member)
    assert resp_member.status_code == 403

    # Admin user can add document
    req_admin = factory.post("/api/v1/llm/rag/documents/", data=payload, format="json")
    force_authenticate(req_admin, user=admin_user)
    resp_admin = view(req_admin)
    assert resp_admin.status_code == 200
    assert resp_admin.data["status"] == "success"

    # Admin user can delete document
    del_payload = {"action": "delete", "doc_id": "test_unauth_doc", "soft": False}
    req_del = factory.post("/api/v1/llm/rag/documents/", data=del_payload, format="json")
    force_authenticate(req_del, user=admin_user)
    resp_del = view(req_del)
    assert resp_del.status_code == 200
    assert resp_del.data["status"] == "success"
