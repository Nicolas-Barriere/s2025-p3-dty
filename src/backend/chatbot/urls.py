"""
URL configuration for the chatbot module.
"""

from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # Simple chat endpoint for frontend
    path('', views.simple_chat_api, name='simple_chat'),
    
    # Health check
    path('health/', views.chatbot_health_check, name='health_check'),
]
