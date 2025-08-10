"""
Views for the OCR app.

This module contains the logic for handling PDF document uploads, processing
them to extract tables based on document type (NPT, Rebut, Defauts, Kosu),
and providing export options in JSON and Excel formats.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from django.core.files.storage import FileSystemStorage
from django.http import HttpRequest, HttpResponse, FileResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.urls import reverse

from .forms import UploadFileForm
from .models import Document, DocumentType
from .pdf_processor import process_document


def upload_file(request: HttpRequest) -> HttpResponse:
    """Handle the upload and processing of PDF documents.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        HttpResponse: The rendered response with the upload form or redirect to results.
    """
    # Ensure document types exist in database
    _ensure_document_types()
    
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            
            # Check if file is PDF
            if not uploaded_file.name.lower().endswith('.pdf'):
                messages.error(request, 'Please upload a PDF file.')
                return render(request, 'ocrapp/upload.html', {'form': form})
            
            # Get document type from form
            doc_type_code = request.POST.get('document_type', '')
            doc_type = None
            if doc_type_code:
                try:
                    doc_type = DocumentType.objects.get(type_code=doc_type_code)
                except DocumentType.DoesNotExist:
                    pass
            
            # Create Document instance
            document = Document(
                file=uploaded_file,
                original_filename=uploaded_file.name,
                document_type=doc_type
            )
            document.save()
            
            # Process the document
            success = process_document(document)
            
            if success:
                messages.success(request, 'Document processed successfully!')
                return redirect('document_detail', pk=document.pk)
            else:
                messages.error(request, f'Processing failed: {document.error_message}')
                return redirect('document_detail', pk=document.pk)
    else:
        form = UploadFileForm()
    
    # Get all document types for the form
    document_types = DocumentType.objects.all()
    
    context = {
        'form': form,
        'document_types': document_types,
    }
    return render(request, 'ocrapp/upload.html', context)


def document_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Display details of a processed document.
    
    Args:
        request: The incoming HTTP request.
        pk: Primary key of the document.
        
    Returns:
        HttpResponse: The rendered document detail page.
    """
    document = get_object_or_404(Document, pk=pk)
    
    # Parse extracted data for display
    extracted_data = document.extracted_data
    tables = extracted_data.get('tables', []) if extracted_data else []
    
    context = {
        'document': document,
        'extracted_data': extracted_data,
        'tables': tables,
        'has_excel': bool(document.excel_file),
        'has_json': bool(document.json_file),
    }
    return render(request, 'ocrapp/document_detail.html', context)


def document_list(request: HttpRequest) -> HttpResponse:
    """Display list of all uploaded documents.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        HttpResponse: The rendered document list page.
    """
    documents = Document.objects.all().select_related('document_type')
    
    context = {
        'documents': documents,
    }
    return render(request, 'ocrapp/document_list.html', context)


def download_excel(request: HttpRequest, pk: int) -> HttpResponse:
    """Download the Excel export of a document.
    
    Args:
        request: The incoming HTTP request.
        pk: Primary key of the document.
        
    Returns:
        FileResponse: The Excel file download.
    """
    document = get_object_or_404(Document, pk=pk)
    
    if not document.excel_file:
        messages.error(request, 'Excel file not available for this document.')
        return redirect('document_detail', pk=pk)
    
    response = FileResponse(
        document.excel_file.open('rb'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{document.original_filename.rsplit(".", 1)[0]}_extracted.xlsx"'
    return response


def download_json(request: HttpRequest, pk: int) -> HttpResponse:
    """Download the JSON export of a document.
    
    Args:
        request: The incoming HTTP request.
        pk: Primary key of the document.
        
    Returns:
        FileResponse: The JSON file download.
    """
    document = get_object_or_404(Document, pk=pk)
    
    if not document.json_file:
        messages.error(request, 'JSON file not available for this document.')
        return redirect('document_detail', pk=pk)
    
    response = FileResponse(
        document.json_file.open('rb'),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="{document.original_filename.rsplit(".", 1)[0]}_extracted.json"'
    return response


def view_json(request: HttpRequest, pk: int) -> JsonResponse:
    """View the extracted data as JSON response.
    
    Args:
        request: The incoming HTTP request.
        pk: Primary key of the document.
        
    Returns:
        JsonResponse: The extracted data as JSON.
    """
    document = get_object_or_404(Document, pk=pk)
    
    return JsonResponse(document.extracted_data, safe=False, json_dumps_params={'indent': 2})


@require_http_methods(["POST"])
def reprocess_document(request: HttpRequest, pk: int) -> HttpResponse:
    """Reprocess a document.
    
    Args:
        request: The incoming HTTP request.
        pk: Primary key of the document.
        
    Returns:
        HttpResponse: Redirect to document detail page.
    """
    document = get_object_or_404(Document, pk=pk)
    
    # Update document type if provided
    doc_type_code = request.POST.get('document_type', '')
    if doc_type_code:
        try:
            doc_type = DocumentType.objects.get(type_code=doc_type_code)
            document.document_type = doc_type
            document.save()
        except DocumentType.DoesNotExist:
            pass
    
    # Reprocess the document
    success = process_document(document)
    
    if success:
        messages.success(request, 'Document reprocessed successfully!')
    else:
        messages.error(request, f'Reprocessing failed: {document.error_message}')
    
    return redirect('document_detail', pk=pk)


def _ensure_document_types():
    """Ensure all document types exist in the database."""
    types = [
        ('NPT', 'NPT Document - Contains structured tables specific to NPT format'),
        ('REBUT', 'Rebut Document - Contains rejection/return related tables'),
        ('DEFAUTS', 'Defauts Document - Contains defect/issue tracking tables'),
        ('KOSU', 'Kosu Document - Contains Kosu specific data tables'),
    ]
    
    for type_code, description in types:
        DocumentType.objects.get_or_create(
            type_code=type_code,
            defaults={'description': description}
        )
