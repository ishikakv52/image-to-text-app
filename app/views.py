from django.shortcuts import render
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
from deep_translator import GoogleTranslator
from langdetect import detect
import cv2
import numpy as np
import tempfile
import os
import io
import re

# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
if os.getenv("RENDER"):
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

def normalize_ocr_token(token):
    token = token.replace('\\', '')
    token = token.replace('/', '')
    token = token.replace('|', 'I')
    token = token.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    token = token.replace('©', 'o').replace('®', 'o')
    if any(c.isalpha() for c in token):
        token = token.replace('0', 'O')
        token = token.replace('1', 'l')
        token = token.replace('5', 'S')
        token = token.replace('6', 'G')
    token = token.replace('rn', 'm')
    token = token.replace('vv', 'w')
    return token

def clean_ocr_text(text):
    if not text:
        return text
    text = re.sub(r'\|+', 'I', text)
    text = re.sub(r'\\+', '', text)
    text = re.sub(r'(?<=\w)-\n(?=\w)', '', text)
    text = re.sub(r'\s+', ' ', text)
    tokens = re.split(r'([\W_]+)', text)
    cleaned = []
    for token in tokens:
        if token and re.match(r'^[A-Za-z]+$', token):
            cleaned.append(normalize_ocr_token(token))
        else:
            cleaned.append(token)
    return ''.join(cleaned).strip()

def deskew_image(image_cv):
    """
    Deskew image if it's rotated - with error handling
    """
    try:
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        coords = np.column_stack(np.where(gray > gray.mean()))
        
        if len(coords) < 10:  # Not enough points to calculate angle
            return image_cv
            
        angle = cv2.minAreaRect(coords)[2]
        
        if angle < -45:
            angle = 90 + angle
        
        if abs(angle) < 1:  # Too small angle, skip
            return image_cv
            
        (h, w) = image_cv.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_cv, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        
        return rotated
    except:
        return image_cv

def preprocess_handwritten_image(image):
    """
    Fast preprocessing for handwritten text detection
    """
    try:
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        image_cv = deskew_image(image_cv)
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
        return Image.fromarray(cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB))
    except Exception as e:
        print(f"Preprocessing error: {e}")
        return image

def extract_text_from_image(image, is_handwritten=False):
    """
    Extract text from image with support for handwritten text using a faster Tesseract pipeline
    """
    try:
        if is_handwritten:
            processed_image = preprocess_handwritten_image(image)
            raw_text = pytesseract.image_to_string(
                image,
                config='--psm 3 --oem 3 -l eng'
            )
            processed_text = pytesseract.image_to_string(
                processed_image,
                config='--psm 6 --oem 1 -l eng'
            )
            text = processed_text if len(processed_text.strip()) >= len(raw_text.strip()) else raw_text
        else:
            text = pytesseract.image_to_string(
                image,
                config='--psm 3 --oem 3 -l eng'
            )
        
        return clean_ocr_text(text.strip()) if text else ""
    except Exception as e:
        return f"Error: {str(e)}"

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

    if request.method == "POST":
        image = request.FILES.get('image')
        is_handwritten = request.POST.get('is_handwritten') == 'on'  # Get handwritten checkbox

        if image:
            lang = request.POST.get("language")
            file_content = image.read()
            
            try:
                if image.name.lower().endswith('.pdf'):
                    # Process PDF from bytes without saving to disk
                    pages = convert_from_bytes(file_content)
                    for page in pages:
                        text += extract_text_from_image(page, is_handwritten=is_handwritten) + "\n"
                else:
                    # Process image directly from memory
                    img = Image.open(io.BytesIO(file_content))
                    text = extract_text_from_image(img, is_handwritten=is_handwritten)
            except Exception as e:
                text = f"Error processing file: {str(e)}"

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