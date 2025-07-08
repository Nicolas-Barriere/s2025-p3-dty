"""
URL configuration for the chatbot module.
"""

from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # AI-powered intelligent email search
    path('intelligent-search/', views.intelligent_search_api, name='intelligent_search'),
    
    # General conversation endpoint
    path('conversation/', views.conversation_api, name='conversation'),
    
    # Chatbot status and configuration
    path('status/', views.chatbot_status_api, name='chatbot_status'),
    
]
