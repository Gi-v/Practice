"""
URL configuration for carbon_calculator project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('emission_app.urls')),
]