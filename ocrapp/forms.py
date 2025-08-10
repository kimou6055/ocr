"""
Forms for the OCR app.

The ``UploadFileForm`` is a simple form with a single file field that
allows users to upload scanned documents. Django automatically handles
validation of the uploaded file and integrates with the views to process
the file.
"""
from __future__ import annotations

from django import forms


class UploadFileForm(forms.Form):
    """A form for uploading a single file."""

    file = forms.FileField(label='Select a scanned document')
