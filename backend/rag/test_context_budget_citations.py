"""Regression tests for Issue 3: Context Budget Enforcement and Citation Validation.

Verifies:
1. Oversized first passage (9,000 chars) is strictly bounded within the 4,000-character limit.
2. Framing tags (<evidence doc=...>), headings, and separators are included in character budget.
3. Oversized individual paragraphs (> max_chunk_chars) are split cleanly during chunking.
4. When budget is exhausted, excluded second passage is dropped from context.
5. A provider response citing the excluded second passage is rejected as a fabricated citation.
6. Citations to included sources remain valid.
7. Distinction between valid source IDs and semantic/factual correctness.
"""
import pytest
from rag.engine import (
    PolicyDocument,
    build_bounded_evidence_context,
    call_llm,
    load_and_chunk_documents,
    validate_provider_response,
)


def test_oversized_first_passage_strictly_bounded_to_4000_chars():
    """Oversized first passage of 9,000 characters must NEVER push final context over 4,000 chars."""
    huge_text = "Greenleaf Clinic appointment policy details. " * 200  # ~9,000 characters
    assert len(huge_text) >= 9000

    passages = [{"doc_name": "massive_policy.txt", "chunk_id": 0, "text": huge_text}]

    context_str, included = build_bounded_evidence_context(passages, max_chars=4000)

    # 1. Final string length must NEVER exceed configured budget (4,000 chars)
    assert len(context_str) <= 4000
    assert len(context_str) > 3800  # Efficiently utilizes available budget
    assert len(included) == 1
    # 2. Framing tags are present and included in budget
    assert '<evidence doc="massive_policy.txt" chunk="0">' in context_str
    assert context_str.endswith("</evidence>")
    # 3. Text in included matches truncated text in block
    assert included[0]["text"] in context_str


def test_framing_and_separators_included_in_budget():
    """Framing tags (<evidence>), XML attributes, and \\n\\n separators are counted in the budget."""
    passages = [
        {"doc_name": "p1.txt", "chunk_id": 0, "text": "A" * 200},
        {"doc_name": "p2.txt", "chunk_id": 1, "text": "B" * 200},
        {"doc_name": "p3.txt", "chunk_id": 2, "text": "C" * 200},
    ]

    limit = 500
    context_str, included = build_bounded_evidence_context(passages, max_chars=limit)

    assert len(context_str) <= limit
    # The formatted string length counts all characters including \n\n separators
    blocks = context_str.split("\n\n")
    assert len(blocks) == len(included)
    total_len = sum(len(b) for b in blocks) + 2 * (len(blocks) - 1)
    assert len(context_str) == total_len


def test_oversized_individual_paragraphs_split_during_chunking():
    """A policy file with an oversized single paragraph (> 600 chars) is split into safe chunks."""
    from unittest.mock import MagicMock, patch

    huge_paragraph = "Critical clinic safety standard sentence number one. " * 40  # ~2,100 chars without \n\n
    assert len(huge_paragraph) > 1500

    mock_doc = PolicyDocument(
        doc_id="huge_para.txt",
        doc_name="huge_para.txt",
        content=huge_paragraph,
        status="APPROVED",
    )

    with patch("rag.engine.get_policy_registry") as mock_reg_fn:
        mock_reg = MagicMock()
        mock_reg.get_approved_documents.return_value = [mock_doc]
        mock_reg_fn.return_value = mock_reg

        chunks = load_and_chunk_documents(max_chunk_chars=600, overlap_chars=100)
        assert len(chunks) >= 3, "Expected 2100-char single paragraph to be split into at least 3 chunks"
        for c in chunks:
            assert len(c.text) <= 600, f"Chunk exceeded max_chunk_chars: {len(c.text)} > 600"
            assert c.doc_name == "huge_para.txt"


def test_excluded_second_passage_dropped_and_rejected_in_citation():
    """When Passage A consumes the budget, Passage B is dropped, and citing Passage B is rejected."""
    # Passage A fits, Passage B is excluded
    passages = [
        {"doc_name": "included_source.txt", "chunk_id": 0, "text": "Y" * 1500},
        {"doc_name": "excluded_source.txt", "chunk_id": 1, "text": "Z" * 1500},
    ]

    context_str, included = build_bounded_evidence_context(passages, max_chars=2000)

    # Passage B must NOT be in the formatted context or in included passages
    assert len(included) == 1
    assert included[0]["doc_name"] == "included_source.txt"
    assert "excluded_source.txt" not in context_str

    # Provider cites the excluded source -> citation validation must strictly reject
    bad_provider_output = {
        "answer": "Appointments require valid photo identification.",
        "citations": ["excluded_source.txt"],
        "confidence": "HIGH",
        "out_of_scope": False,
        "safety_flag": False,
    }

    with pytest.raises(ValueError, match="Fabricated citation detected.*excluded_source.txt"):
        validate_provider_response(bad_provider_output, included)


def test_included_source_citation_accepted():
    """Citations pointing to actually included sources pass schema validation."""
    passages = [
        {"doc_name": "valid_policy.txt", "chunk_id": 0, "text": "Valid policy text here."}
    ]
    context_str, included = build_bounded_evidence_context(passages, max_chars=1000)

    valid_provider_output = {
        "answer": "Appointments require valid photo identification.",
        "citations": ["valid_policy.txt"],
        "confidence": "HIGH",
        "out_of_scope": False,
        "safety_flag": False,
    }

    validated = validate_provider_response(valid_provider_output, included)
    assert validated["citations"] == ["valid_policy.txt"]


def test_call_llm_rejects_hallucinated_citation_from_dropped_evidence():
    """call_llm rejects a provider response that cites a passage dropped by the context budgeter."""
    passages = [
        {"doc_name": "admitted.txt", "chunk_id": 0, "text": "W" * 3980},
        {"doc_name": "dropped.txt", "chunk_id": 1, "text": "This evidence was dropped."},
    ]

    # Mock provider invents citation to dropped.txt
    def hallucinating_mock_provider(prompt):
        return {
            "answer": "Clinic requires pre-registration.",
            "citations": ["dropped.txt"],
            "confidence": "HIGH",
            "out_of_scope": False,
            "safety_flag": False,
        }

    res = call_llm(
        question="How do I register?",
        context_passages=passages,
        mock_provider=hallucinating_mock_provider,
        bypass_rate_limit=True,
    )
    # Must trigger safe generic public fallback error because citation validation failed
    assert res["citations"] == []
    assert "error" in res or res["answer"].startswith("The FAQ assistant is temporarily unavailable")


def test_source_id_validation_does_not_claim_factual_entailment():
    """Validating a source ID verifies that the cited ID exists in supplied context,

    not that the claim is logically or factually entailed by the passage content.
    """
    passages = [{"doc_name": "factual_context.txt", "text": "Clinic opens at 8am."}]
    payload = {
        "answer": "The moon is made of green cheese.",
        "citations": ["factual_context.txt"],
        "confidence": "HIGH",
        "out_of_scope": False,
        "safety_flag": False,
    }
    # Schema check succeeds because factual_context.txt was provided
    validated = validate_provider_response(payload, passages)
    assert validated["citations"] == ["factual_context.txt"]
    # Semantic verification confirms this is unentailed/unsupported
    from rag.evaluation import verify_unsupported_claim
    is_grounded = verify_unsupported_claim(payload["answer"], passages)
    assert is_grounded is False, "A claim unsupported by passage facts must fail entailment check!"
