# gemini_utils.py
import fitz  # PyMuPDF
import os
from pathlib import Path
from PIL import Image
import google.generativeai as genai

# Set your Gemini API key
genai.configure(api_key="AIzaSyCaepqj4cvBjIoM_frul2WCzE2tKEFhbSc")

def extract_details(image_path,prompt):
    # # === Step 1: Convert PDF to Image ===
    # pdf_path = Path(pdf_path_str)  # Convert string to Path object
    # base_filename = pdf_path.stem
    # image_filename = f"converted_{base_filename}.jpg"
    # image_path = os.path.join("uploads", image_filename)

    # doc = fitz.open(str(pdf_path))  # PyMuPDF requires str path
    # page = doc.load_page(0)
    # pix = page.get_pixmap(dpi=00)
    # pix.save(image_path)
    # print(f"✅ Image saved: {image_path}")

    # === Step 2: Send to Gemini ===
    model = genai.GenerativeModel("gemini-2.5-flash")
    if image_path !='':
        img = Image.open(image_path)
        response = model.generate_content([prompt, img])
    else:
        response = model.generate_content([prompt])
    
    print("✅ Gemini response received")

    return response.text
