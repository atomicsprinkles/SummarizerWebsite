from django.shortcuts import render

from django.http import FileResponse
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
import tempfile

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
    AnxietySet = {4, 6, 7, 10, 13, 21, "amygdala"}
    SalienceSet = {8, 9, 10, 13, 22, 23, 24, 25, 29, 30, 31, 32, 33}
    ExecFuncSet = {7, 8, 9, 10, 11, 19, 22, 37, 40, 46}
    AttentionSet = {6, 7, 8, 9, 19, 39, 40}
    MoodSet = {10, 11, 13, 23, 24, 32, 33, 44, 45, 47}
    DefauModeSet = {2, 7, 10, 11, 19, 29, 30, 31, 35, 39, 40}
    AddicRewardSet = {13, 24, 35, 32, 34, 44, 45, 46, 47}
    LangSet = {22, 39, 40, 41, 42, 44, 45}

    text = ""
    #pattern = r"BA (?:Left|Right) (\d+(?:,\s*\d+)*)"

    pattern = r"BA (?:Left |Right )?(\d+(?:, \d+)*)(?: \((\d+(?:, \d+)*)\))?"
    #pattern = r"BA (?:Left|Right )?([(\d+,)]+\s?(?:\(\d+,\s?\d+\))?(?:, \d+)*)"


    numshown = set()
    pdf_ids = request.session.get("pdf_ids", [])
    processedfiles = []

    for pdf_id in pdf_ids:
        pdf_instance = uploadedPDFiles.objects.get(pk=pdf_id)
        if pdf_instance.processed_pdf:
            continue
        with open(pdf_instance.original_pdf.path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            writer = PyPDF2.PdfWriter()
            baseline_reader = PyPDF2.PdfReader(open(baselinepath, "rb"))
            writer.add_page(baseline_reader.pages[0])
            
            for i in range(min(len(reader.pages), 2)):
                writer.add_page(reader.pages[i])
            
            text = reader.pages[1].extract_text()
            txet = reader.pages[1].extract_text()
            if "Eyes Closed: Brain Map Source" in text:
                index = txet.index("Eyes Closed: Brain Map Source") + len("Eyes Closed: Brain Map Source")
                txet = txet[index:]
            number_text = re.findall(pattern, txet)
            numshown = set()
            for primary, associated in number_text:
                primary_numbers = primary.split(',')
                associated_numbers = associated.split(',') if associated else []
                for number in primary_numbers + associated_numbers:
                    if number.strip():
                        numshown.add(int(number.strip()))
            print(txet)
        name_line = re.search(r"^(.+?)\r?\nGender:", text, re.MULTILINE)
        name_line = name_line.group(1)
        name_line = re.sub(r"Weight:\s*\d+\s*lbs\s*Height:\s*\d+\s*ft\s*\d+\s*in", "", name_line)
        name = name_line.strip()
        gender = re.search(r"Gender:\s*(Male|Female)", text)
        age = re.search(r"Age:\s*(\d+)\s*\(DOB:", text)
        date = re.search(r"Exam Date:\s*([A-Za-z]+ \d{1,2} \d{4} \d{2}:\d{2})", text)
        orge = re.search(r"Exam Date:[^\n]*\n(.*?)(?:\n|$)", text, re.DOTALL)
        orge = orge.group(1)

        pdfbytes = io.BytesIO()
        writer.write(pdfbytes)
        pdfbytes.seek(0)
        doc = fitz.open("pdf", pdfbytes)
        Page = doc[0]
        
        sets = [
            (AnxietySet, 290, 210),
            (ExecFuncSet, 420, 260),
            (AttentionSet, 475, 400),
            (MoodSet, 420, 525),
            (DefauModeSet, 290, 580),
            (AddicRewardSet, 160, 530),
            (LangSet, 110, 400),
            (SalienceSet, 160, 260)
        ]   

        def calculate_match_percentage(numshown, set_name):
            return 100 - round(len(numshown.intersection(set_name)) / len(set_name) * 100)
        
        texts_to_add = [{"text": f"{calculate_match_percentage(numshown, set_name)}%", "x": x, "y": y} for set_name, x, y in sets]
        data_to_add = [
            {"text": f"Patient Name: {name if name else 'Not Available'}", "x": 60, "y": 120},
            {"text": f"Gender: {gender.group(1) if gender else 'Not Available'}", "x": 60, "y": 130},
            {"text": f"Age: {age.group(1) if age else 'Not Available'}", "x": 60, "y": 140},
            {"text": f"Exam Date: {date.group(1) if date else 'Not Available'}", "x": 430, "y": 130},
            {"text": f"Organization: {orge if orge else 'Not Available'}", "x": 420, "y": 140},
        ]

        for item in texts_to_add:
            text, x, y = item['text'], item['x'], item['y']
            Page.insert_text((x, y), text, fontsize=14, color=(0, 0, 0))
        for item in data_to_add:
            text, x, y = item["text"], item["x"], item["y"]
            Page.insert_text((x, y), text, fontsize=9, color=(0, 0, 0))
        Page.insert_text((150, 700), "This is not an extension of BrainView (manufacturer) software-generated report.", fontsize=8, color=(0,0,0))
        g = f"{name if name else 'Not Available'}"
        temp_file_path = f'{g.replace(" ", "")}.pdf'
        doc.save(temp_file_path)
        temp_file_path.replace(" ", "")
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
    for file_path in processedfiles:
        os.remove(file_path)


    return response