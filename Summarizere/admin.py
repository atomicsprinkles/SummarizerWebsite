from django.contrib import admin
from .models import UserInformation, uploadedPDFiles

admin.site.register(UserInformation)
admin.site.register(uploadedPDFiles)