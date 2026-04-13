from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from deep_translator import GoogleTranslator
from langdetect import detect
import uuid
import os
# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
if os.getenv("RENDER"):
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

def landing(request):
    return render(request, "landing.html")


def app_page(request):
    return render(request, "app.html")


def upload_image(request):
    text = ""
    translated_text = ""

    lang_codes = {
        'original': None,
        'detect': 'detect',
        'en': 'en',
        'zh': 'zh-CN',
        'es': 'es',
        'hi': 'hi',
        'ar': 'ar',
        'bn': 'bn',
        'pt': 'pt',
        'ru': 'ru',
        'ja': 'ja',
        'pa': 'pa',
        'de': 'de',
        'fr': 'fr',
        'ms': 'ms',
        'vi': 'vi',
        'ko': 'ko',
        'as': 'as',
        'doi': 'doi',
        'gu': 'gu',
        'kn': 'kn',
        'gom': 'gom',
        'mai': 'mai',
        'ml': 'ml',
        'mni-Mtei': 'mni-Mtei',
        'mr': 'mr',
        'ne': 'ne',
        'or': 'or',
        'sa': 'sa',
        'sd': 'sd',
        'ta': 'ta',
        'te': 'te',
        'ur': 'ur',
    }

    # ✅ FIX ONLY HERE
    if request.method == "POST":
        image = request.FILES.get('image')  # FIXED LINE

        if image:
            lang = request.POST.get("language")

            fs = FileSystemStorage()
            unique_filename = f"{uuid.uuid4()}_{image.name}"
            filename = fs.save(unique_filename, image)
            file_path = fs.path(filename)

            if filename.lower().endswith('.pdf'):
                pages = convert_from_path(file_path)
                for page in pages:
                    text += pytesseract.image_to_string(page) + "\n"
            else:
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img)

            if lang == "original":
                translated_text = text
            elif lang == "detect":
                try:
                    detected_lang = detect(text)
                    translated_text = f"Detected Language: {detected_lang.upper()}"
                except Exception:
                    translated_text = "Language detection failed"
            else:
                target = lang_codes.get(lang)
                if target:
                    translated_text = GoogleTranslator(
                        source='auto',
                        target=target
                    ).translate(text)
                else:
                    translated_text = "Translation not supported for this language"

    return render(request, "app.html", {
        "text": text,
        "translated_text": translated_text
    })