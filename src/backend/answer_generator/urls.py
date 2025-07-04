"""
URL configuration for the email response generator.
"""

from django.urls import path
from . import views

app_name = 'answer_generator'

urlpatterns = [
    # Generate email response endpoint
    path('answer_generator/generate-email-response/', views.generate_email_response, name='generate_email_response'),
]
