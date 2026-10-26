from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from mlcore import registry
from predictions.access import IsAdminOrMember
from predictions.serializers import PredictionInputSerializer


def _unavailable(error):
    return Response({"detail": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ModelInfoView(APIView):
    """GET /api/v1/ml/model: facts about the model, plus the input ranges for building forms."""

    permission_classes = [IsAdminOrMember]

    def get(self, request):
        try:
            loaded = registry.load_model()
        except registry.ModelUnavailable as error:
            return _unavailable(error)
        return Response(registry.public_model_info(loaded.metadata))


class NoShowPredictView(APIView):
    """POST /api/v1/ml/no-show/predict: one fictional appointment in, a probability out.

    Stateless: nothing is saved, and no profile data is ever read.
    """

    permission_classes = [IsAdminOrMember]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = PredictionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            loaded = registry.load_model()
        except registry.ModelUnavailable as error:
            return _unavailable(error)
        return Response(registry.predict_one(loaded, serializer.validated_data))