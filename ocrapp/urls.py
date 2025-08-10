"""
URL configuration for the OCR app.

This module defines the URL patterns for PDF document upload, processing,
viewing, and export functionality.
"""
from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path('', views.upload_file, name='upload_file'),
    path('documents/', views.document_list, name='document_list'),
    path('document/<int:pk>/', views.document_detail, name='document_detail'),
    path('document/<int:pk>/excel/', views.download_excel, name='download_excel'),
    path('document/<int:pk>/json/', views.download_json, name='download_json'),
    path('document/<int:pk>/view-json/', views.view_json, name='view_json'),
    path('document/<int:pk>/reprocess/', views.reprocess_document, name='reprocess_document'),
]
