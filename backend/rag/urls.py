from django.urls import path

from rag.views import (
    AdvancedRAGEval20View,
    AdvancedRAGSearchView,
    DocumentManagementView,
    PolicyFAQEvaluateView,
    PolicyFAQView,
)

urlpatterns = [
    path("faq", PolicyFAQView.as_view(), name="llm-faq"),
    path("faq/evaluate", PolicyFAQEvaluateView.as_view(), name="llm-faq-evaluate"),
    path("rag/search", AdvancedRAGSearchView.as_view(), name="rag-search"),
    path("rag/eval-20", AdvancedRAGEval20View.as_view(), name="rag-eval-20"),
    path("rag/documents", DocumentManagementView.as_view(), name="rag-documents"),
]
