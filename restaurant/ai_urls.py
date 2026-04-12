from django.urls import path

from . import ai_views

app_name = 'ai'

urlpatterns = [
    path('', ai_views.ai_studio, name='studio'),
    path('generate-name/', ai_views.ai_generate_name, name='generate_name'),
    path('generate-content/', ai_views.ai_generate_content, name='generate_content'),
]
