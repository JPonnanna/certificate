from flask import Flask, request, render_template, redirect, url_for, flash, session
import os
from werkzeug.utils import secure_filename
from helper import extract_details  # Assumes AI processing
from qr_utils import extract_qr_and_download  # Handles QR + download
from imgconvert import convert_pdf_to_image
import json
from report_generator import generate_verification_report
from test1 import *
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flashing messages

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ✅ Check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ✅ Route: Upload form and file handling
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(saved_path)

            return redirect(url_for('process_file', filename=filename))
        else:
            flash('File type not allowed')
            return redirect(request.url)

    return render_template('home.html')


# ✅ Route: AI processing with Gemini (optional)
@app.route('/process/<filename>')
def process_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img_path=convert_pdf_to_image(filepath)
    # # Optional: Skip Gemini AI if not required for QR
    # prompt = """
    # Extract all academic certificate information from this image.
    # Return a JSON object with:
    # - data1: extracted fields (e.g. Name, Roll Number, Institution, Course, Issue Date, Marks, etc.)
    # - isScanned: true if the document is a scanned or xerox copy
    # - isCropped: true if the document has cropped edges or bad orientation
    # Only return the JSON object.
    # """
    # gemini_response = extract_details(img_path,prompt)
    # print("🧠 Gemini AI response:", gemini_response)

    return redirect(url_for('qr_extract', filename=filename,img_path=img_path))


# ✅ Route: QR extraction and download
@app.route('/qr_extract/<filename>')
def qr_extract(filename):
    # ✅ Derive corresponding image filename (used earlier in conversion step)
    base_name = filename.rsplit('.', 1)[0]
    image_filename = f"converted_{base_name}.jpg"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

    # ✅ Pass the converted image to the QR extractor
    result = extract_qr_and_download(
        image_path,
        app.config['UPLOAD_FOLDER'],
        base_name
    )
    
    if result['status'] == 'success':
        saved=result['saved_as']
        session['fetched_pdf_link'] = result['url']
        # return render_template("qr_fetch.html", url=result['url'], saved=result['saved_as'])
        return redirect(url_for('convert_and_process', filename=filename,saved=saved))
    else:
        mes=f"❌ QR Extraction Failed: {result['error']}"
        return render_template('failedqr.html',message=mes)

@app.route('/convert_and_process/<filename>')
def convert_and_process(filename):
    saved = request.args.get('saved')
    img_path2=convert_pdf_to_image(saved)
    # prompt = """
    # Extract all academic certificate information from this image.
    # Return a JSON object with:
    # - data2: extracted fields (e.g. Name, Roll Number, Institution, Course, Issue Date, Marks, etc.)
    # Only return the JSON object.
    # """
    # gemini_response = extract_details(img_path2,prompt)
    # print("🧠 Gemini AI response:", gemini_response)

    return redirect(url_for('extract_from_llm', filename=filename))



@app.route('/extract_from_llm/<filename>')
def extract_from_llm(filename):
    base_name = filename.rsplit('.', 1)[0]

    # Step 1: Original uploaded image
    image_filename = f"converted_{base_name}.jpg"
    img_path1 = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

    prompt1 = """
    Extract all relevant academic certificate information from this image.

    Return a JSON object with:
    - data: an object containing all identifiable fields from the certificate related to academic details (e.g., Name, Roll Number, Institution, Course, Issue Date, Marks, etc.).
    - For tabular data (such as marks, results, or grades), extract each row as a structured object with keys like "Subject", "Code", "Internal Marks", "External Marks", "Total", "Grade", or similar — based on what's available. Store all such rows in a list under the key "Marks". 
    - Do not assume any fixed table structure. Instead, intelligently interpret column headers and map them to fields in the row.
    - metadata: a separate object that should capture **non-academic** technical or system-generated fields such as:
        - CID
        - Issued By (if it refers to a blockchain entity or digital issuer)
        - Issue Timestamp or Blockchain Issue Date
        - Wallet Address, Hash, Signature, QR-related information, or any other verifiable blockchain or issuance identifiers
    If any such fields are present visually or explicitly, extract them under this key.
    - isScanned: true if the document appears to be a scanned or xerox copy.
    - isCropped: true if the document appears to have cropped edges or incorrect orientation.

    **Rules:**
    - If marks or result data is presented in a table (any format), normalize it into a consistent list of objects.
    - Avoid hallucinating data — only return what is explicitly visible and identifiable in the document.
    - Do **not** include null values for fields that are missing.
    - Do **not** include academic fields in the metadata section and vice versa.
    - Only return the JSON object. Do not include any extra explanations or messages.

    Return format example:
    {
    "data": {
        "Name": "ADAM CLARKE",
        "Institution": "LARANA HIGH SCHOOL",
        "Course": "5TH STANDARD",
        "Issue Date": "15/07/2025",
        "Marks": [
        {
            "Subject": "SOFTWARE ENGINEERING AND PROJECT MANAGEMENT",
            "Code": "21CS61",
            "Internal Marks": "39",
            "External Marks": "30",
            "Total": "69",
            "Result": "P",
            "Announced On": "2024-09-06"
        },
        {
            "Subject": "SOFTWARE TESTING",
            "Code": "21CS63",
            "Internal Marks": "40",
            "External Marks": "40",
            "Total": "80",
            "Result": "P",
            "Announced On": "2024-09-06"
        }
        ]
    },
    "metadata": {
        "CID": "bafkreia...",
        "Issued By": "0x52F...8E2",
        "Issue Timestamp": "2024-09-06T10:30:00Z",
        "Signature": "QmTcY...hash",
        "Wallet Address": "0xabc123..."
    },
    "isScanned": false,
    "isCropped": false
    }
    """

    actual = extract_details(img_path1, prompt1)
    print("📄 Actual data (uploaded):", actual)

    # Step 2: QR-downloaded image
    image_filename2 = f"converted_{base_name}_qr.jpg"
    img_path2 = os.path.join(app.config['UPLOAD_FOLDER'], image_filename2)

    contextual_prompt = f"""
    The following JSON object has already been extracted from another version of the same academic certificate image:

    {json.dumps(actual, indent=2)}

    Use this reference to maintain consistency in field naming and structure.

    Now extract all relevant academic certificate information from the new image provided.

    Return a JSON object with:
    - "data": an object containing all identifiable academic fields from the certificate (e.g., Name, Roll Number, Institution, Course, Issue Date, Marks, etc.).
    - If academic information is shown in table format (like marks, grades, or results), extract each row as a structured object. Use dynamic and context-aware mapping of headers to fields such as:
    "Subject", "Code", "Internal Marks", "External Marks", "Total", "Grade", "Result", "Announced On", or similar, based on what's visible.
    Store all rows under the "Marks" key as a list.
    - Do not assume any fixed table layout — interpret column headers intelligently and extract data accordingly.
    - Do **not** include blockchain-related metadata such as:
    - CID
    - Issued By
    - Issued Time
    - Any hash, signature, or QR-related values  
    These must be completely excluded from the output (not even as null).
    - If the image contains valid academic fields that are *not* present in the original reference JSON, include them.
    - Do **not** invent or hallucinate any fields — only include data that is clearly and confidently identifiable from the document.
    - Return two boolean flags:
    - "isScanned": true if the document appears to be a scanned/photocopy.
    - "isCropped": true if the document shows signs of being cropped or poorly aligned.

    Return only the final JSON object in this format:

    {{
    "data": {{
        ... all clearly visible and valid academic fields ...
    }}

    }}
    """

    original = extract_details(img_path2, contextual_prompt)
    print("📥 Original data (from QR):", original)

    # Step 3: Store both results in session
    session['actual'] = actual
    session['original'] = original

    session['uploaded_pdf'] = filename
    


    # Step 4: Redirect to comparison route
    return redirect(url_for('compare_certificates'))

# @app.route('/extract_from_llm/<filename>')
# def extract_from_llm(filename):
#     base_name = filename.rsplit('.', 1)[0]
#     image_filename = f"converted_{base_name}.jpg"
#     img_path1 = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

#     # Step 2: Extract details from original image
#     prompt = """
#     Extract all academic certificate information from this image.
#     Return a JSON object with:
#     - data1: extracted fields (e.g. Name, Roll Number, Institution, Course, Issue Date, Marks, etc.)
#     - isScanned: true if the document is a scanned or xerox copy
#     - isCropped: true if the document has cropped edges or bad orientation
#     Only return the JSON object.
#     """
#     actual = extract_details(img_path1, prompt)
#     print("📄 Actual data (uploaded):", actual)

#     # Step 3: Extract QR and download certificate
#     image_filename2 = f"converted_{base_name}_qr.jpg"
#     img_path2 = os.path.join(app.config['UPLOAD_FOLDER'], image_filename2)

#     prompt = """
#     Extract all academic certificate information from this image.
#     Return a JSON object with:
#     - data2: extracted fields (e.g. Name, Roll Number, Institution, Course, Issue Date, Marks, etc.)
#     Only return the JSON object.
#     """
#     # Step 5: Extract details from QR-downloaded image
#     original = extract_details(img_path2, prompt)
#     print("📥 Original data (from QR):", original)

#     # Step 6: Pass both JSONs to final comparison route
#     return redirect(url_for('compare_certificates', actual=json.dumps(actual), original=json.dumps(original)))

@app.route('/compare_certificates')
def compare_certificates():
    actual = session.get('actual')
    original = session.get('original')

    if not actual or not original:
        return "❌ Missing certificate data in session.", 400

    # Create comparison prompt
    compare_prompt = f"""
    You are verifying two academic certificates.

    Certificate A (Original Upload):
    {json.dumps(actual, indent=2)}

    Certificate B (Downloaded via QR):
    {json.dumps(original, indent=2)}

    You are an AI verifier responsible for assessing the authenticity of an academic certificate by comparing two sources:

    "Uploaded" — data extracted from the user-uploaded document (stored in variable actual)

    "Stored on blockchain" — data retrieved by decoding the QR code embedded in the certificate (stored in variable original)

    Your task is to perform a detailed comparison and return a multi-paragraph, user-friendly report in natural, professional language. Avoid technical details or JSON output. The output should be suitable for a consumer-facing application. Structure your response in four sections as described below, using short, clear paragraphs. No headings.

    Strict Constraint: Do not state or highlight any data that is present in 'original/Stored on the blockchain, but was not in 'actual'/Uploaded . This may be because of the Text Extraction not happening properly.The 'original'/Stored on Blockchain is the truth and is ultimate.
        First line of the respone is a starting point like 'This certificate seems to be Original'(Only if all the fields match), and it is categorically stated in the last paragraph. else 'The certificate is most likely forged or edited', and it is categorically concluded in the end
    1. Field Comparison
    Compare the following fields if they are present in both certificates: Name, Roll Number, Institution, Course, Issue Date, and Marks.
    If all fields match, say:
    “All key fields in the uploaded certificate match the official blockchain record.”
    If mismatches are found, clearly state each discrepancy like:
    “The uploaded certificate lists the student name as 'John Doe', while the official record lists it as 'Jon Doe'.”
    Do not mention fields that match—only list mismatches.
    It is okay if some field is present in variable 'original' or stored on the blockchain, but was not listed in the 'actual'or /Uploaded data
    Dont highlight any missing fields in the 'actual' or uploaded data, but never miss highlighthing and stating mismatched values from 'original'or as stored on the blockchain.
    If any critical field (e.g. Name or Roll Number) is missing in the uploaded certificate, say:
    “Some essential information, such as the student name or roll number, is missing from the uploaded certificate, which limits the reliability of verification.”

    2. QR Code Data and Field Agreement
    If QR code data could not be extracted or is empty, say:
    “The QR code could not be read or did not contain valid certificate data. Verification could not be performed.”
    If QR data is available, and fields match, say:
    "Comparison between the uploaded document and blockchain certificate was made.”
    Also state:
    “All the fields match” or “Fields do not match  — depending on whether discrepancies were found.
    Note: Dont highlight any missing fields in the 'actual' or uploaded data, but never miss highlighthing and stating mismatched values from 'original'or as stored on the blockchain.

    3. Document Condition
    Based on the scanned and cropped metadata flags, infer the document type for users without using technical terms.

    If both flags are false and all records match: say “The uploaded certificate is a digital copy in its original form.”

    If both flags are false and records dont match: Dont say anything

    If isScanned is true: say “The uploaded certificate appears to be a scanned copy.”

    If isCropped is true: say “The uploaded certificate appears to have been cropped or has layout inconsistencies.”

    If both are true: combine the above two.

    4. Conclusion
    Provide a final determination based on the comparison:

    If no mismatches:
    “The certificate is authentic and accurately reflects the official record.” Note:' Dont highlight any missing fields in the 'actual' or uploaded data, but never miss highlighthing and stating mismatched values from 'original'or as stored on the blockchain.'

    If mismatches are found:
    “The certificate has inconsistencies and is not authentic. Discrepancies were found between the uploaded and official certificate data.”

    If QR code or essential fields are missing:
    “The authenticity of the certificate could not be verified due to missing or incomplete data.”
    """
    actual_cleaned = (actual.strip().strip('"').replace("```json\n", "").replace("```", ""))
    original_cleaned = (original.strip().strip('"').replace("```json\n", "").replace("```", ""))
    actual_json=json.loads(actual_cleaned)
    original_json=json.loads(original_cleaned)
    verified=verify_certificate(actual_json,original_json)
    print(verified)
    #result = trained_llama("",verified)
    result=generate_verification_report(verified)
    #print(result)
    uploaded_pdf = session.get('uploaded_pdf')
    fetched_pdf_url = session.get('fetched_pdf_link')
    return render_template("result.html", result=result.lstrip(), uploaded_pdf=uploaded_pdf, fetched_pdf_url=fetched_pdf_url)


@app.route('/about')
def about():
    return render_template('about.html')

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    #app.run(debug=True)
    app.run()
