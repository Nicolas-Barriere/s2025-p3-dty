"""API ViewSet for evaluating and comparing AI prompts"""

import rest_framework as drf
from rest_framework import mixins, status, viewsets, permissions, serializers as drf_serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    inline_serializer
)
from rest_framework.response import Response
from rest_framework.decorators import action
from core import models

from .. import serializers

@extend_schema(tags=["prompt-evaluation"])
class PromptEvaluationViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
):
    queryset = models.PromptEvaluation.objects.all()
    serializer_class = serializers.PromptEvaluationSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'destroy']:
            return [permissions.IsAdminUser()]
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    @extend_schema(
        request=inline_serializer(
            name="PromptEvaluationRequest",
            fields={
                "prompt_id": drf_serializers.IntegerField(help_text="ID du prompt évalué."),
                "prompt_type": drf_serializers.CharField(help_text="Type du prompt (ex: new_mail, answer_mail)."),
                "accepted": drf_serializers.BooleanField(help_text="L'utilisateur a-t-il accepté la suggestion ?"),
            },
        ),
        responses={
            201: OpenApiResponse(
                response={"type": "object", "properties": {
                    "id": {"type": "integer"},
                    "prompt_id": {"type": "integer"},
                    "prompt_type": {"type": "string"},
                    "accepted": {"type": "boolean"},
                    "created_at": {"type": "string", "format": "date-time"},
                }},
                description="Prompt evaluation successfully created.",
            ),
            403: OpenApiResponse(
                response={"detail": "Permission denied"},
                description="User is not authenticated.",
            ),
        },
        tags=["prompt-evaluation"]
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="evaluate",
        url_name="evaluate",
    )
    def evaluate_prompt(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        evaluation = models.PromptEvaluation.objects.create(
            prompt_id=data.get("prompt_id"),
            prompt_type=data.get("prompt_type"),
            accepted=data.get("accepted"),
            # Ajoute ici user si tu as un champ user dans le modèle
        )
        serializer = self.get_serializer(evaluation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)