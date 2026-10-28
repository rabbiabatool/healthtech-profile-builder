from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import AdminSessionAuthentication, CookieJWTAuthentication
from mlcore import registry
from predictions.access import IsAdminOrMember
from predictions.serializers import PredictionInputSerializer, PredictionResultSerializer

ML_TAG = "No-show estimate (educational ML)"

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=True,
    description="CSRF token from GET /api/auth/csrf (members) or GET /api/admin/csrf (admins).",
)

UNAUTHENTICATED = OpenApiResponse(description="Not signed in, or the session or token has expired.")
FORBIDDEN = OpenApiResponse(description="Not allowed: wrong role or missing CSRF token.")
UNAVAILABLE = OpenApiResponse(
    description="The model is missing or failed its integrity check. Run python -m mlcore.train."
)


def _unavailable(error):
    return Response({"detail": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class MlBaseView(APIView):
    """Members sign in with the JWT cookie, admins with the admin session."""

    authentication_classes = [CookieJWTAuthentication, AdminSessionAuthentication]
    permission_classes = [IsAdminOrMember]


class ModelInfoView(MlBaseView):
    @extend_schema(
        summary="About the no-show model",
        description=(
            "Model version, training facts, headline metrics, risk-band cut-points, limitations and the "
            "allowed input ranges (used to build forms). Educational prototype on synthetic data."
        ),
        tags=[ML_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Public model facts."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def get(self, request):
        try:
            loaded = registry.load_model()
        except registry.ModelUnavailable as error:
            return _unavailable(error)
        return Response(registry.public_model_info(loaded.metadata))


class NoShowPredictView(MlBaseView):
    """One fictional appointment in, a probability out. Stateless: nothing is saved."""

    parser_classes = [JSONParser]

    @extend_schema(
        summary="Estimate the no-show likelihood of one appointment",
        description=(
            "Strictly validated: wrong types, out-of-range values, unknown fields, NaN and impossible "
            "combinations are rejected with 400, never silently fixed. Nothing is stored and no profile "
            "data is used. Educational prototype on synthetic data: not clinically validated and not "
            "medical advice."
        ),
        tags=[ML_TAG],
        request=PredictionInputSerializer,
        parameters=[CSRF_HEADER],
        responses={
            200: PredictionResultSerializer,
            400: OpenApiResponse(description="Validation failed. The body maps field names to lists of messages."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def post(self, request):
        serializer = PredictionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            loaded = registry.load_model()
        except registry.ModelUnavailable as error:
            return _unavailable(error)
        return Response(registry.predict_one(loaded, serializer.validated_data))