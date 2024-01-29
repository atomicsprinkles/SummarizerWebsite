from django import forms
import PyPDF2
from django.core.exceptions import ValidationError
from .models import uploadedPDFiles

def validate_pdf_file(value):
    try:
        pdf = PyPDF2.PdfReader(value)
        if len(pdf.pages) == 0:
            raise ValidationError("The selected file is not a valid PDF.")
    except PyPDF2.utils.PdfReadError:
        raise ValidationError("The selected file is not a valid PDF.")

class PDFUploadForm(forms.ModelForm):
    class Meta:
        model = uploadedPDFiles
        fields = ['original_pdf']

    files = forms.FileField(required=False)
