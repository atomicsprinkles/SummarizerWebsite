from django.db import models

class UserInformation(models.Model):
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)

class uploadedPDFiles(models.Model):
    original_pdf = models.FileField(upload_to='pdfs/')
    processed_pdf = models.FileField(upload_to='processed_pdfs/', null=True, blank=True)