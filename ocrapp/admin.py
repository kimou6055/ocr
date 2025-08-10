"""
Admin configuration for the OCR app.

This module registers the Document and DocumentType models with the Django
admin interface for easy management.
"""
from django.contrib import admin
from .models import Document, DocumentType


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    """Admin configuration for DocumentType model."""
    list_display = ['type_code', 'description', 'created_at']
    search_fields = ['type_code', 'description']
    ordering = ['type_code']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin configuration for Document model."""
    list_display = ['original_filename', 'document_type', 'status', 'table_count', 'uploaded_at', 'processed_at']
    list_filter = ['status', 'document_type', 'uploaded_at']
    search_fields = ['original_filename']
    readonly_fields = ['uploaded_at', 'processed_at', 'extracted_data', 'error_message']
    ordering = ['-uploaded_at']
    
    fieldsets = (
        ('File Information', {
            'fields': ('file', 'original_filename', 'document_type')
        }),
        ('Processing Status', {
            'fields': ('status', 'error_message', 'uploaded_at', 'processed_at')
        }),
        ('Extraction Results', {
            'fields': ('table_count', 'extracted_data')
        }),
        ('Export Files', {
            'fields': ('excel_file', 'json_file')
        }),
    )
