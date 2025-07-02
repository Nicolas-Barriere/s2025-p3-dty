"""
API ViewSet for AI
"""

import logging
from rest_framework import viewsets
from rest_framework.decorators import action
import rest_framework as drf

from .. import permissions, utils, serializers
from ..serializers import AITransformSerializer, AITranslateSerializer
from messages.chatbot import get_chatbot, AlbertChatbot
from core.services.ai_services import AIService


logger = logging.getLogger(__name__)

class DocumentViewSet(viewsets.GenericViewSet):
    @action(
        detail=True, 
        methods=["post"], 
        name="Apply a transformation action on a piece of text with AI", 
        url_path="ai-transform", 
        throttle_classes=[utils.AIDocumentRateThrottle, utils.AIUserRateThrottle],
    )
    def ai_transform(self, request, *args, **kwargs):
        """
        POST /api/v1.0/documents/<resource_id>/ai-transform
        with expected data:
        - text: str
        - action: str [prompt, correct, rephrase, summarize]
        Return JSON response with the processed text.
        """
        # Check permissions first
        self.get_object()

        serializer = serializers.AITransformSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        action = serializer.validated_data["action"]

        response = AIService().transform(text, action)

        return drf.response.Response(response, status=drf.status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        name="Translate a piece of text with AI",
        url_path="ai-translate",
        throttle_classes=[utils.AIDocumentRateThrottle, utils.AIUserRateThrottle],
    )
    def ai_translate(self, request, *args, **kwargs):
        """
        POST /api/v1.0/documents/<resource_id>/ai-translate
        with expected data:
        - text: str
        - language: str [settings.LANGUAGES]
        Return JSON response with the translated text.
        """
        # Check permissions first
        self.get_object()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        language = serializer.validated_data["language"]

        response = AIService().translate(text, language)

        return drf.response.Response(response, status=drf.status.HTTP_200_OK)