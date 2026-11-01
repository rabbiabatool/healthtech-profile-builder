from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from accounts.permissions import IsStandardUser
from mlcore import registry
from predictions.serializers import PredictionInputSerializer

ML_TAG = "No-show estimate (educational ML)"

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=True,
    description="CSRF token from GET /api/auth/csrf.",
)

UNAUTHENTICATED = OpenApiResponse(description="Not signed in, or the session or token has expired.")
FORBIDDEN = OpenApiResponse(description="Not allowed: wrong role or missing CSRF token.")
UNAVAILABLE = OpenApiResponse(
    description="The model is missing or failed its integrity check. Run python -m mlcore.train."
)


def _unavailable(error):
    return Response({"detail": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class MemberMLBaseView(APIView):
    """Base class for member-only ML endpoints.

    Uses CookieJWTAuthentication (reads the HttpOnly access_token cookie) and
    IsStandardUser (role == USER only). This matches the member profile guard
    pattern and strictly blocks:
      - anonymous callers -> 401
      - admin accounts (role == ADMIN or admin session) -> 401 / 403
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser]


class ModelInfoView(MemberMLBaseView):
    """GET /api/v1/ml/model: facts about the model, plus the input ranges for building forms."""

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


class NoShowPredictView(MemberMLBaseView):
    """POST /api/v1/ml/no-show/predict: one fictional appointment in, a probability out.

    Stateless: nothing is saved, and no profile data is ever read.
    """

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
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Prediction probability and risk band."),
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
