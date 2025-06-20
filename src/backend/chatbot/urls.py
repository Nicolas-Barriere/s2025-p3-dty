"""
URL configuration for the chatbot module.
"""

from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # Simple chat endpoint for frontend
    path('', views.simple_chat_api, name='simple_chat'),
    
    # Class-based API view (handles multiple operations)
    path('api/', views.ChatbotAPIView.as_view(), name='chatbot_api'),
    
    # DRF function-based API views
    path('api/summarize/', views.summarize_mail_api, name='summarize_mail'),
    path('api/answer/', views.generate_answer_api, name='generate_answer'),
    path('api/classify/', views.classify_mail_api, name='classify_mail'),
    path('api/batch/', views.batch_process_api, name='batch_process'),
    
    # Health check
    path('health/', views.chatbot_health_check, name='health_check'),
]
