from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from deep_translator import GoogleTranslator
from langdetect import detect
import uuid

pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'


def landing(request):
    return render(request, "landing.html")


def app_page(request):
    return render(request, "app.html")


def upload_image(request):
    text = ""
    translated_text = ""

    lang_codes = {
        'original': None,
        'detect': 'detect',  # Special for language detection
        'en': 'en',
        'zh': 'zh-CN',  # Mandarin Chinese (simplified)
        'es': 'es',  # Spanish
        'hi': 'hi',
        'ar': 'ar',  # Arabic
        'bn': 'bn',  # Bengali
        'pt': 'pt',  # Portuguese
        'ru': 'ru',  # Russian
        'ja': 'ja',  # Japanese
        'pa': 'pa',  # Punjabi
        'de': 'de',  # German
        'fr': 'fr',  # French
        'ms': 'ms',  # Malay
        'vi': 'vi',  # Vietnamese
        'ko': 'ko',  # Korean
        'as': 'as',  # Assamese
        'doi': 'doi',  # Dogri
        'gu': 'gu',  # Gujarati
        'kn': 'kn',  # Kannada
        'gom': 'gom',  # Konkani
        'mai': 'mai',  # Maithili
        'ml': 'ml',  # Malayalam
        'mni-Mtei': 'mni-Mtei',  # Manipuri
        'mr': 'mr',  # Marathi
        'ne': 'ne',  # Nepali
        'or': 'or',  # Odia
        'sa': 'sa',  # Sanskrit
        'sd': 'sd',  # Sindhi
        'ta': 'ta',  # Tamil
        'te': 'te',  # Telugu
        'ur': 'ur',  # Urdu
    }

    if request.method == "POST" and request.FILES['image']:
        image = request.FILES['image']
        lang = request.POST.get("language")

        fs = FileSystemStorage()
        unique_filename = f"{uuid.uuid4()}_{image.name}"
        filename = fs.save(unique_filename, image)
        file_path = fs.path(filename)

        if filename.lower().endswith('.pdf'):
            # Convert PDF to images
            pages = convert_from_path(file_path)
            for page in pages:
                text += pytesseract.image_to_string(page) + "\n"
        else:
            # Assume it's an image
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)

        if lang == "original":
            translated_text = text
        elif lang == "detect":
            try:
                detected_lang = detect(text)
                translated_text = f"Detected Language: {detected_lang.upper()}"
            except Exception as e:
                translated_text = "Language detection failed"
        else:
            target = lang_codes.get(lang)
            if target:
                translated_text = GoogleTranslator(source='auto', target=target).translate(text)
            else:
                translated_text = "Translation not supported for this language"

    return render(request, "app.html", {
        "text": text,
        "translated_text": translated_text
    })