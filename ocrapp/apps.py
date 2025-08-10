from __future__ import annotations

from django.apps import AppConfig


class OcrappConfig(AppConfig):
    """Configuration for the OCR app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ocrapp'
    verbose_name = 'OCR Application'
