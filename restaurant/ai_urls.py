from django.urls import path

from . import ai_views
from . import coach_views

app_name = 'ai'

urlpatterns = [
    path('', ai_views.ai_studio, name='studio'),
    path('generate-name/', ai_views.ai_generate_name, name='generate_name'),
    path('generate-content/', ai_views.ai_generate_content, name='generate_content'),

    # AI โค้ชพนักงาน
    path('coach/', coach_views.coach_team, name='coach_team'),
    path('coach/suggest/', coach_views.coach_suggest, name='coach_suggest'),
]
