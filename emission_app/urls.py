"""
URL configuration for the emission_app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('activity/', views.activity, name='activity'),
    path('history/', views.history, name='history'),
    path('delete/<int:record_id>/', views.delete_record, name='delete_record'),
]