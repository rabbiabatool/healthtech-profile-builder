from django.urls import path

from rag.views import PolicyFAQEvaluateView, PolicyFAQView

urlpatterns = [
    path("faq", PolicyFAQView.as_view(), name="llm-faq"),
    path("faq/evaluate", PolicyFAQEvaluateView.as_view(), name="llm-faq-evaluate"),
]

