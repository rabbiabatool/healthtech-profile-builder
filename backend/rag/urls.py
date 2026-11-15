from django.urls import path

from rag.views import (
    PolicyDocumentApproveView,
    PolicyDocumentListView,
    PolicyFAQEvaluateView,
    PolicyFAQView,
)

urlpatterns = [
    path("faq", PolicyFAQView.as_view(), name="llm-faq"),
    path("faq/evaluate", PolicyFAQEvaluateView.as_view(), name="llm-faq-evaluate"),
    path("policies", PolicyDocumentListView.as_view(), name="llm-policies"),
    path("policies/<str:doc_name>/approve", PolicyDocumentApproveView.as_view(), name="llm-policies-approve"),
]
