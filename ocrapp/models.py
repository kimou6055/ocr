"""
Database models for the OCR app.

This module contains models for storing uploaded PDF documents, their types,
and extracted table data. The system supports four document types: NPT, Rebut,
Defauts, and Kosu, each with their own table extraction logic.
"""
from __future__ import annotations

from django.db import models
from django.core.files.storage import default_storage
import json


class DocumentType(models.Model):
    """Model to store different document types."""
    
    TYPE_CHOICES = [
        ('NPT', 'NPT'),
        ('REBUT', 'Rebut'),
        ('DEFAUTS', 'Defauts'),
        ('KOSU', 'Kosu'),
    ]
    
    type_code = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        unique=True,
        help_text="Document type identifier"
    )
    description = models.TextField(
        blank=True, 
        help_text="Description of the document type and its structure"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Document Type'
        verbose_name_plural = 'Document Types'
        ordering = ['type_code']
    
    def __str__(self) -> str:
        return self.type_code


class Document(models.Model):
    """Model to store uploaded documents and extraction results."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Processing'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    # File and metadata
    file = models.FileField(
        upload_to='uploads/%Y/%m/%d/', 
        help_text="Uploaded PDF file"
    )
    original_filename = models.CharField(
        max_length=255, 
        help_text="Original name of the uploaded file"
    )
    document_type = models.ForeignKey(
        DocumentType, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Type of document (NPT, Rebut, Defauts, Kosu)"
    )
    
    # Processing status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING',
        help_text="Current processing status"
    )
    error_message = models.TextField(
        blank=True, 
        help_text="Error message if processing failed"
    )
    
    # Extraction results
    extracted_data = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Extracted table data in JSON format"
    )
    table_count = models.IntegerField(
        default=0, 
        help_text="Number of tables extracted"
    )
    
    # Export files
    excel_file = models.FileField(
        upload_to='exports/excel/%Y/%m/%d/', 
        blank=True, 
        null=True,
        help_text="Generated Excel file"
    )
    json_file = models.FileField(
        upload_to='exports/json/%Y/%m/%d/', 
        blank=True, 
        null=True,
        help_text="Generated JSON file"
    )
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-uploaded_at']
    
    def __str__(self) -> str:
        return f"{self.original_filename} ({self.get_status_display()})"
    
    def get_extracted_data_preview(self) -> str:
        """Return a preview of extracted data."""
        if self.extracted_data:
            data_str = json.dumps(self.extracted_data, indent=2)
            if len(data_str) > 500:
                return data_str[:500] + "..."
            return data_str
        return "No data extracted"
    
    def delete(self, *args, **kwargs):
        """Override delete to remove associated files."""
        # Delete the uploaded file
        if self.file:
            default_storage.delete(self.file.name)
        
        # Delete export files
        if self.excel_file:
            default_storage.delete(self.excel_file.name)
        if self.json_file:
            default_storage.delete(self.json_file.name)
        
        super().delete(*args, **kwargs)
