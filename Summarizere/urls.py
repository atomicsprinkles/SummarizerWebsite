
#BrainView/urls.py

from django.urls import path
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='login'), name="landing_page"),
    path('login/', views.login_view, name='login'),
    path('signUp/', views.register, name='signUp'),
    path('summarizer/', views.upload_pdf, name="summarizer"),
    path('EEGProcessed/', views.process_pdf, name='process_pdf')

]
