from pathlib import Path
import fitz
import os

def convert_pdf_to_image(pdf_path_str, output_folder='uploads', zoom=4):
    pdf_path = Path(pdf_path_str)
    base_filename = pdf_path.stem
    image_filename = f"converted_{base_filename}.jpg"
    image_path = os.path.join(output_folder, image_filename)

    doc = fitz.open(str(pdf_path))
    page = doc.load_page(0)

    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    pix.save(image_path)
    print(f"✅ Image saved: {image_path}")
    return image_path
