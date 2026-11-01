from django.urls import path

from predictions.views import (
    ClusteringAnalysisView,
    ModelInfoView,
    NoShowPredictView,
    SupervisedComparisonView,
)

urlpatterns = [
    path("model", ModelInfoView.as_view(), name="ml-model"),
    path("models/comparison", SupervisedComparisonView.as_view(), name="ml-models-comparison"),
    path("clusters", ClusteringAnalysisView.as_view(), name="ml-clusters"),
    path("no-show/predict", NoShowPredictView.as_view(), name="ml-no-show-predict"),
]
