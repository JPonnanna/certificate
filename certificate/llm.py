import fitz  # PyMuPDF
import uuid
import os
from PIL import Image
import google.generativeai as genai

def extract_details(pdf_path):
    # === Step 1: Convert PDF to Image with Unique Filename ===
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=100)

    # Generate a unique filename
    image_filename = f"converted_page_{uuid.uuid4().hex}.jpg"
    image_path = os.path.join("uploads", image_filename)

    # Save the image
    pix.save(image_path)
    print(f"✅ Saved first page as image: {image_path}")

    # === Step 2: Send Image to Gemini ===
    genai.configure(api_key="AIzaSyCaepqj4cvBjIoM_frul2WCzE2tKEFhbSc")
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Load the image
    img = Image.open(image_path)

    prompt = """
    Extract all academic certificate information from this image.
    Return output in JSON format with relevant fields not only limited to Name, Roll Number, Institution, Course, Issue Date, and Marks (if present).
    """

    response = model.generate_content([prompt, img])
    print("✅ Details extracted from image using Gemini")

    # (Optional) Clean up file after processing
    # try:
    #     os.remove(image_path)
    #     print("🧹 Temporary image file removed")
    # except Exception as e:
    #     print("⚠️ Could not remove image file:", e)

    return response.text
