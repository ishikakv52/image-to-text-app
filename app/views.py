from django.shortcuts import render
from PIL import Image, ImageFilter, ImageEnhance
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

def extract_handwritten_text(image):
    """
    Simple and reliable handwritten text extraction
    """
    try:
        # Convert to grayscale
        if isinstance(image, Image.Image):
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Simple preprocessing: threshold + morphology
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Convert back to PIL
        processed_image = Image.fromarray(cleaned)

        # Extract text with basic config
        text = pytesseract.image_to_string(
            processed_image,
            config='--psm 6 --oem 3 -l eng'
        )

        if text.strip():
            return clean_handwriting_text(text.strip())

        # Fallback: try with original image
        text = pytesseract.image_to_string(
            image,
            config='--psm 3 --oem 3 -l eng'
        )

        return clean_handwriting_text(text.strip()) if text.strip() else "No text detected. Please ensure the image is clear and contains readable text."

    except Exception as e:
        return f"Error: {str(e)}"
    """
    Simple and reliable handwritten text extraction
    """
    try:
        # Convert to grayscale
        if isinstance(image, Image.Image):
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Simple preprocessing: threshold + morphology
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Convert back to PIL
        processed_image = Image.fromarray(cleaned)

        # Extract text with basic config
        text = pytesseract.image_to_string(
            processed_image,
            config='--psm 6 --oem 3 -l eng'
        )

        if text.strip():
            return clean_handwriting_text(text.strip())

        # Fallback: try with original image
        text = pytesseract.image_to_string(
            image,
            config='--psm 3 --oem 3 -l eng'
        )

        return clean_handwriting_text(text.strip()) if text.strip() else "No text detected. Please ensure the image is clear and contains readable text."

    except Exception as e:
        return f"Error: {str(e)}"

def clean_handwriting_text(text):
    """
    Clean and normalize handwritten OCR text with handwriting-specific fixes
    """
    if not text:
        return text

    # Remove excessive whitespace and newlines
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'\s+', ' ', text)

    # Common OCR fixes for handwriting
    text = text.replace('\\', '')
    text = text.replace('|', 'I')
    text = text.replace('/', '')
    text = text.replace('©', 'o')
    text = text.replace('®', 'o')
    text = text.replace('™', 'tm')

    # Fix common letter confusions in handwriting
    text = re.sub(r'\b1\b', 'I', text)  # 1 -> I
    text = re.sub(r'\b0\b', 'O', text)  # 0 -> O
    text = re.sub(r'\b5\b', 'S', text)  # 5 -> S
    text = re.sub(r'\b6\b', 'G', text)  # 6 -> G
    text = re.sub(r'\b8\b', 'B', text)  # 8 -> B
    text = re.sub(r'\b2\b', 'Z', text)  # 2 -> Z
    text = re.sub(r'\b3\b', 'E', text)  # 3 -> E
    text = re.sub(r'\b4\b', 'A', text)  # 4 -> A
    text = re.sub(r'\b7\b', 'T', text)  # 7 -> T
    text = re.sub(r'\b9\b', 'g', text)  # 9 -> g

    # Fix common word fragments and letter combinations
    text = re.sub(r'\bth(\w)', r'th\1', text)  # the -> the
    text = re.sub(r'\ban(\w)', r'an\1', text)  # and -> and
    text = re.sub(r'\bin(\w)', r'in\1', text)  # ing -> ing
    text = re.sub(r'\ber(\w)', r'er\1', text)  # er -> er
    text = re.sub(r'\bre(\w)', r're\1', text)  # re -> re

    # Fix common handwriting mistakes
    text = re.sub(r'\brn\b', 'm', text)  # rn -> m
    text = re.sub(r'\bvv\b', 'w', text)  # vv -> w
    text = re.sub(r'\bll\b', 'll', text)  # ll -> ll (keep as is)
    text = re.sub(r'\btt\b', 'tt', text)  # tt -> tt (keep as is)

    # Fix punctuation issues
    text = re.sub(r'([a-zA-Z])(\.)([a-zA-Z])', r'\1. \3', text)  # Add space after period
    text = re.sub(r'([a-zA-Z])(,)([a-zA-Z])', r'\1, \3', text)  # Add space after comma

    # Remove isolated punctuation at line starts/ends
    text = re.sub(r'^\W+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\W+$', '', text, flags=re.MULTILINE)

    # Capitalize first letter of sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    capitalized_sentences = []
    for sentence in sentences:
        if sentence.strip():
            capitalized_sentences.append(sentence.strip().capitalize())
    text = '. '.join(capitalized_sentences)

    return text.strip()

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
    Extract text from image with support for handwritten text using advanced methods
    """
    try:
        if is_handwritten:
            # Use specialized handwritten text extraction
            return extract_handwritten_text(image)
        else:
            # Standard OCR for printed text
            text = pytesseract.image_to_string(
                image,
                config='--psm 3 --oem 3 -l eng'
            )
            return clean_handwriting_text(text.strip()) if text else ""
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