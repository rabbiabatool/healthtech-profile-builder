from django.urls import path

from predictions.views import ModelInfoView, NoShowPredictView

urlpatterns = [
    path("model", ModelInfoView.as_view(), name="ml-model"),
    path("no-show/predict", NoShowPredictView.as_view(), name="ml-no-show-predict"),
]