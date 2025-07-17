"""API ViewSet for sharing some public settings."""

from django.conf import settings

import rest_framework as drf
from rest_framework.permissions import AllowAny


class ConfigView(drf.views.APIView):
    """API ViewSet for sharing some public settings."""

    permission_classes = [AllowAny]

    def get(self, request):
        """
        GET /api/v1.0/config/
            Return a dictionary of public settings.
        """
        array_settings = [
            "ENVIRONMENT",
            "FRONTEND_THEME",
            "MEDIA_BASE_URL",
            "POSTHOG_KEY",
            "LANGUAGES",
            "LANGUAGE_CODE",
            "SENTRY_DSN",
        ]
        dict_settings = {}
        for setting in array_settings:
            if hasattr(settings, setting):
                dict_settings[setting] = getattr(settings, setting)

        # AI_ENABLED logic: True if all required AI settings are set and not default/empty
        ai_enabled = False
        ai_key = getattr(settings, "AI_API_KEY", None)
        ai_base_url = getattr(settings, "AI_BASE_URL", None)
        ai_model = getattr(settings, "AI_MODEL", None)
        if (
            ai_key not in (None, "", "default","<my-ai-api-key>")
            and ai_base_url not in (None, "", "default")
            and ai_model not in (None, "", "default")
        ):
            ai_enabled = True
        dict_settings["AI_ENABLED"] = ai_enabled

        return drf.response.Response(dict_settings)
