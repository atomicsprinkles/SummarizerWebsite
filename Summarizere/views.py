from django.shortcuts import render

from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from .models import UserInformation, uploadedPDFiles
from django.contrib.staticfiles import finders

from .forms import PDFUploadForm

import math
import os
import PyPDF2
import re
import fitz
import io
import zipfile

hardcoded_passkey = "123abc"


@csrf_protect
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')
        passkey = request.POST.get("passkey")


        try:
            user = UserInformation.objects.get(email=email, password=password)
            if passkey == hardcoded_passkey:
                request.session['user_id'] = user.id
                request.session['logged_in'] = True
                return redirect('summarizer')
            else:
                messages.error(request, 'Invalid username or password.')
        except UserInformation.DoesNotExist:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'Login.html')

# Assuming you have a predefined passkey


@csrf_protect
def register(request):
    if request.method == 'POST':
        firstname = request.POST['firstname']
        lastname = request.POST['lastname']
        email = request.POST['username']
        password = request.POST['password']
        input_passkey = request.POST['passkey']

        if input_passkey != hardcoded_passkey:
            return HttpResponse("Invalid passkey.")

        if UserInformation.objects.filter(email=email).exists():
            return HttpResponse("This email has already been used.")

        user_info = UserInformation(firstname=firstname, lastname=lastname, email=email, password=password)
        user_info.save()

        return redirect("login")
    return render(request, 'SignUp.html')

@csrf_exempt
def upload_pdf(request):
    if not request.session.get('logged_in'):
        return redirect('login')
    
    if request.method == 'POST':
        files = request.FILES.getlist('original_pdf')
        pdf_ids = []
        for f in files:
            form = PDFUploadForm(request.POST, {'original_pdf': f})
            if form.is_valid():
                pdf_instance = form.save()
                pdf_ids.append(pdf_instance.pk)
        request.session["pdf_ids"] = pdf_ids
        return redirect('process_pdf')
    else:
        form = PDFUploadForm()

    return render(request, "upload_pdf.html", {'form': form})



def process_pdf(request):
    baselinepath = finders.find('Summarizer.pdf')
    AnxietySet = {4, 6, 7, 10, 13, 21}
    SalienceSet = {8, 9, 10, 13, 22, 23, 24, 25, 29, 30, 31, 32, 33}
    ExecFuncSet = {7, 8, 9, 10, 11, 19, 22, 37, 40, 46}
    AttentionSet = {6, 7, 8, 9, 19, 39, 40}
    MoodSet = {10, 11, 13, 23, 24, 32, 33, 44, 45, 47}
    DefauModeSet = {2, 7, 10, 11, 19, 29, 30, 31, 35, 39, 40}
    AddicRewardSet = {13, 24, 35, 32, 34, 44, 45, 46, 47}
    LangSet = {22, 39, 40, 41, 42, 44, 45}
    text = ""
    pattern = r"BA (?:Right|Left) ([\d, \(\)]+)"
    numshown = set()
    pdf_ids = request.session.get("pdf_ids", [])
    processedfiles = []

    for pdf_id in pdf_ids:
        pdf_instance = uploadedPDFiles.objects.get(pk=pdf_id)
        if pdf_instance.processed_pdf:
            return render(request, 'result.html', {'pdf_instance': pdf_instance})
        with open(pdf_instance.original_pdf.path, 'rb') as pdf_file:
            Reader = PyPDF2.PdfReader(pdf_file)
            Writer = PyPDF2.PdfWriter()
            for i in range(len(Reader.pages)):
                if i < 2:
                    b = Reader.pages[i]
                    Writer.add_page(b)
            basereader = PyPDF2.PdfReader(open(baselinepath, "rb"))
            Writer.add_page(basereader.pages[0])
            text += Reader.pages[1].extract_text()
            numfound = set(re.findall(pattern, text))
            for match in numfound:
                integers = [int(item) for item in re.findall(r'\d+', match)]
                for integer in integers:
                    numshown.add(integer)
        pdfbytes = io.BytesIO()
        Writer.write(pdfbytes)
        pdfbytes.seek(0)
        doc = fitz.open("pdf", pdfbytes)
        Page = doc[2]
        texts_to_add = [
            {"text": f"{math.ceil(len(numshown.intersection(AnxietySet)) / len(AnxietySet) * 100)}%", "x": 290, "y": 210},
            {"text": f"{math.ceil(len(numshown.intersection(ExecFuncSet)) / len(ExecFuncSet) * 100)}%", "x": 420, "y": 260},
            {"text": f"{math.ceil(len(numshown.intersection(AttentionSet)) / len(AttentionSet) * 100)}%", "x": 475, "y": 400},
            {"text": f"{math.ceil(len(numshown.intersection(MoodSet)) / len(MoodSet) * 100)}%", "x": 420, "y": 525},
            {"text": f"{math.ceil(len(numshown.intersection(DefauModeSet)) / len(DefauModeSet) * 100)}%", "x": 290, "y": 580},
            {"text": f"{math.ceil(len(numshown.intersection(AddicRewardSet)) / len(AddicRewardSet) * 100)}%", "x": 160, "y": 530},
            {"text": f"{math.ceil(len(numshown.intersection(LangSet)) / len(LangSet) * 100)}%", "x": 110, "y": 400},
            {"text": f"{math.ceil(len(numshown.intersection(SalienceSet)) / len(SalienceSet) * 100)}%", "x": 160, "y": 260},
        ]
        for item in texts_to_add:
            text, x, y = item['text'], item['x'], item['y']
            Page.insert_text((x, y), text, fontsize=14, color=(0, 0, 0))

        temp_file_path = 'temp_modified_pdf.pdf'
        doc.save(temp_file_path)
        doc.close()

        processedfiles.append(temp_file_path)

    zip_filename = "processed_pdf(s).zip"

    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for i in processedfiles:
            zipf.write(i)
    buffer = io.BytesIO()
    with open(zip_filename, 'rb') as f:
        buffer.write(f.read())

    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Dispositon'] = f"attachment; filename='{zip_filename}'"

    os.remove(zip_filename)

    for d in pdf_ids:
        pdf_instance = uploadedPDFiles.objects.get(pk=d)
        os.remove(pdf_instance.original_pdf.path)
        pdf_instance.delete()

    return response