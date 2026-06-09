from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from llm import extract_details
from pinata import upload_to_pinata

import os
import qrcode
from io import BytesIO
import datetime
import tempfile

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import white
from reportlab.lib.utils import ImageReader

from PyPDF2 import PdfReader, PdfWriter


app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
GENERATED_FOLDER = "generated"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/")
def landing():
    return render_template("unified.html")

@app.route('/test')
def test():
    return render_template('base.html')

@app.route("/process_certificate", methods=["POST"])
def process_certificate():
    print('got cert')
    pdf = request.files["pdf"]
    filename = secure_filename(pdf.filename)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    pdf.save(pdf_path)

    pdf_reader = PdfReader(open(pdf_path, 'rb'))
    pdf_writer = PdfWriter()
    
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        if page.mediabox.width > page.mediabox.height:
            page.rotate(-90)  
        pdf_writer.add_page(page)
    
    # Overwrite original with corrected orientation
    with open(pdf_path, 'wb') as corrected_pdf:
        pdf_writer.write(corrected_pdf)

    # Step 1: Fetch latest ID (mock or from frontend)
    latest_cert_id = request.form.get("latest_cert_id", "0")
    next_cert_id = int(latest_cert_id) + 1

    # Step 2: Get timestamp
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Step 3: Upload original PDF to IPFS
    ipfs_link = upload_to_pinata(pdf_path)
    cid = ipfs_link.split("/")[-1]  # or extract CID from full IPFS link
    # Save a duplicate copy using the CID
    cid_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{cid}.pdf")
    with open(pdf_path, 'rb') as original, open(cid_pdf_path, 'wb') as duplicate:
        duplicate.write(original.read())

    # Step 4: Extract details using your LLM OCR system
    details = extract_details(pdf_path)
    print(details)
    #details=''

    return jsonify({
    "certificateID": next_cert_id,
    "date": date,
    "ipfs": ipfs_link,  # or just original ipfs_link if QR is only shown later
    "details": details,
    "cid": cid
    })

@app.route("/finalize_certificate", methods=["POST"])
def finalize_certificate():
    data = request.json
    cert_id = data["certId"]
    timestamp = data["timestamp"]
    issuer_address = data["issuer"]
    institution_name = data["institution"]
    ipfs_link = data["ipfs_link"]
    cid = ipfs_link.split("/")[-1]

    # Load original PDF and get page size
    original_pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{cid}.pdf")
    reader = PdfReader(original_pdf_path)
    page = reader.pages[0]
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)

    # Generate QR code
    qr_img = qrcode.make(ipfs_link)
    qr_path = os.path.join(GENERATED_FOLDER, f"qr_{cid}.png")
    qr_img.save(qr_path)

    # Layout configuration
    qr_size = 70  # slightly smaller
    line_height = 8
    spacing = 2   # minimal spacing between lines
    num_text_lines = 5

    box_width = 160
    box_height = (line_height * num_text_lines) + spacing * (num_text_lines - 1) + qr_size

    x = page_width - box_width
    y = page_height - box_height

    # Create overlay canvas
    overlay_stream = BytesIO()
    c = canvas.Canvas(overlay_stream, pagesize=(page_width, page_height))

    # White background box
    c.setFillColor(white)
    c.rect(x, y, box_width, box_height, fill=1, stroke=0)

    # Draw content
    c.setFillColorRGB(0, 0, 0)
    cy = y + box_height - line_height  # Start from top inside box

    c.setFont("Helvetica", 7)
    c.drawCentredString(x + box_width / 2, cy, f"Certificate ID: {cert_id}")
    cy -= (line_height + spacing)

    c.setFont("Helvetica", 5.5)
    c.drawCentredString(x + box_width / 2, cy, f"CID: {cid}...")
    cy -= (line_height + spacing)

    c.drawImage(ImageReader(qr_path), x + (box_width - qr_size) / 2, cy - qr_size + 5, width=qr_size, height=qr_size)
    cy -= (qr_size - 5 + spacing)

    c.setFont("Helvetica", 7)
    c.drawCentredString(x + box_width / 2, cy, f"Issued: {issuer_address[:3]}...{issuer_address[-4:]}")
    cy -= (line_height + spacing)

    c.drawCentredString(x + box_width / 2, cy, f"Institution: {institution_name}")
    cy -= (line_height + spacing)

    c.drawCentredString(x + box_width / 2, cy, timestamp)

    c.save()
    overlay_stream.seek(0)

    # Merge overlay
    overlay_reader = PdfReader(overlay_stream)
    overlay_page = overlay_reader.pages[0]
    page.merge_page(overlay_page)

    writer = PdfWriter()
    writer.add_page(page)
    for i in range(1, len(reader.pages)):
        writer.add_page(reader.pages[i])

    # Save final PDF
    final_pdf_path = os.path.join(GENERATED_FOLDER, f"final_{cid}.pdf")
    with open(final_pdf_path, "wb") as f:
        writer.write(f)

    # Upload to IPFS
    final_ipfs_link = upload_to_pinata(final_pdf_path)

    return jsonify({
        "final_ipfs_link": final_ipfs_link,
        "cid": cid
    })


# @app.route("/finalize_certificate", methods=["POST"])
# def finalize_certificate():
#     data = request.json
#     cert_id = data["certId"]
#     timestamp = data["timestamp"]
#     issuer_address = data["issuer"]
#     institution_name = data["institution"]
#     ipfs_link = data["ipfs_link"]
#     cid = ipfs_link.split("/")[-1]

#     # Step 1: Generate QR code
#     qr_img = qrcode.make(ipfs_link)
#     qr_path = os.path.join(GENERATED_FOLDER, f"qr_{cid}.png")
#     qr_img.save(qr_path)

#     # Step 2: Determine page size
#     original_pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{cid}.pdf")
#     reader = PdfReader(original_pdf_path)
#     page = reader.pages[0]
#     page_width = float(page.mediabox.width)
#     page_height = float(page.mediabox.height)

#     # Step 3: Determine box position (fallback = bottom-right)
#     box_width = 400
#     box_height = 220

#     fallback_x = page_width - box_width - 40  # right padding
#     fallback_y = 40  # bottom padding

#     x, y = fallback_x, fallback_y  # For now, always fallback (replace this if detection logic is implemented)

#     # Step 4: Create overlay with white box + content
#     overlay_stream = BytesIO()
#     c = canvas.Canvas(overlay_stream, pagesize=(page_width, page_height))

#     # White box
#     c.setFillColor(white)
#     c.rect(x, y, box_width, box_height, fill=1, stroke=0)

#     # Metadata content inside box (centered horizontally)
#     c.setFillColorRGB(0, 0, 0)
#     c.setFont("Helvetica", 12)
#     c.drawCentredString(x + box_width / 2, y + box_height - 30, f"Certificate ID: {cert_id}")
#     c.setFont("Helvetica", 6)
#     c.drawCentredString(x + box_width / 2, y + box_height - 50, f"CID: {cid[:6]}...")
#     c.drawImage(ImageReader(qr_path), x + (box_width - 100) / 2, y + box_height - 160, width=100, height=100)
#     c.setFont("Helvetica", 10)
#     c.drawCentredString(x + box_width / 2, y + 55, f"Issued by: {issuer_address[:3]}...{issuer_address[-4:]}")
#     c.drawCentredString(x + box_width / 2, y + 40, f"Institution: {institution_name}")
#     c.drawCentredString(x + box_width / 2, y + 25, timestamp)

#     c.save()
#     overlay_stream.seek(0)

#     # Step 5: Merge overlay with first page
#     overlay_reader = PdfReader(overlay_stream)
#     overlay_page = overlay_reader.pages[0]

#     writer = PdfWriter()
#     page.merge_page(overlay_page)
#     writer.add_page(page)

#     # Add remaining pages
#     for i in range(1, len(reader.pages)):
#         writer.add_page(reader.pages[i])

#     # Step 6: Save final PDF
#     final_pdf_path = os.path.join(GENERATED_FOLDER, f"final_{cid}.pdf")
#     with open(final_pdf_path, "wb") as f:
#         writer.write(f)

#     # Step 7: Upload to IPFS
#     final_ipfs_link = upload_to_pinata(final_pdf_path)

#     return jsonify({
#         "final_ipfs_link": final_ipfs_link,
#         "cid": cid
#     })



# @app.route("/finalize_certificate", methods=["POST"])
# def finalize_certificate():
#     data = request.json
#     cert_id = data["certId"]
#     timestamp = data["timestamp"]
#     issuer_address = data["issuer"]
#     institution_name = data["institution"]
#     ipfs_link = data["ipfs_link"]
#     cid = ipfs_link.split("/")[-1]
#     # Step 1: Generate QR
#     qr_img = qrcode.make(ipfs_link)
#     qr_path = os.path.join(GENERATED_FOLDER, f"qr_{cid}.png")
#     qr_img.save(qr_path)

#     # Step 2: Generate decorated PDF
#     final_pdf_path = os.path.join(GENERATED_FOLDER, f"final_{cid}.pdf")
#     c = canvas.Canvas(final_pdf_path, pagesize=A4)
#     c.setFont("Helvetica", 12)
#     c.drawString(100, 780, f"Certificate ID: {cert_id}")
#     c.drawString(100, 760, f"CID: {cid}")
#     c.drawString(100, 740, f"Issued by: {issuer_address[:6]}...{issuer_address[-4:]} ({institution_name})")
#     c.drawString(100, 720, f"{timestamp}")
#     c.drawString(100, 700, f"IPFS Link: {ipfs_link}")
#     c.drawImage(qr_path, 100, 580, width=150, height=150)
#     c.showPage()
#     c.save()

#     # Step 3: Upload final PDF to IPFS
#     final_ipfs_link = upload_to_pinata(final_pdf_path)

#     # Step 4: Return
#     return jsonify({ 
#         "final_ipfs_link": final_ipfs_link ,
#         'cid':cid
#     })


import csv
from flask import request, render_template

@app.route("/confirm")
def confirm():
    cid = request.args.get("cid")
    cert_id = request.args.get("certId")
    timestamp = request.args.get("timestamp")
    newipfs = request.args.get("newipfs")
    issuer = request.args.get("issuerid")  # passed via URL

    # Define the CSV file path
    csv_path = os.path.join(os.getcwd(), "certificates.csv")

    # Ensure headers are written if file doesn't exist
    write_header = not os.path.exists(csv_path)

    # Append record
    with open(csv_path, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(["CertificateID", "Timestamp", "IPFS", "Issuer"])
        writer.writerow([cert_id, timestamp, newipfs, issuer])

    return render_template("confirm.html", cid=cid, newipfs=newipfs, cert_id=cert_id, timestamp=timestamp)


@app.route("/institution_certificates/<institutionName>")
def institution_certificates(institutionName):
    certs = []
    with open("certificates.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["Issuer"].lower() == institutionName.lower():
                certs.append(row)
    return render_template("institution_certs.html", certs=certs, institutionName=institutionName)

@app.route("/admin/all_certificates")
def admin_all_certificates():
    certs = []
    with open("certificates.csv", "r") as file:
        reader = csv.DictReader(file)
        certs = list(reader)
    #print(certs)
    print(certs[0]['IPFS'])
    return render_template("admin_certs.html", certs=certs)


    # # Step 5: Generate QR code
    # qr_img = qrcode.make(ipfs_link)
    # qr_path = os.path.join(GENERATED_FOLDER, f"qr_{cid}.png")
    # qr_img.save(qr_path)

    # # Step 6: Generate new PDF with QR and metadata
    # final_pdf_path = os.path.join(GENERATED_FOLDER, f"final_{cid}.pdf")
    # c = canvas.Canvas(final_pdf_path, pagesize=A4)
    # c.setFont("Helvetica", 12)
    # issuer_address = request.form.get("wallet", "")  # from frontend
    # institution_name = request.form.get("inst_name", "Institution")
    # c.drawString(100, 780, f"Certificate ID: {next_cert_id}")
    # c.drawString(100, 760, f"CID: {cid}")
    # c.drawString(100, 740, f"Issued by: {issuer_address[:6]}...{issuer_address[-4:]} ({institution_name})")
    # c.drawString(100, 720, f"IPFS Link: {ipfs_link}")
    # c.drawImage(qr_path, 100, 580, width=150, height=150)
    # c.showPage()
    # c.save()

    # # Step 7: Upload final PDF with QR to IPFS
    # final_ipfs_link = upload_to_pinata(final_pdf_path)

    # # Clean up
    # # os.remove(pdf_path)
    # # os.remove(qr_path)
    # # os.remove(final_pdf_path)

    # # Step 8: Render confirmation page
    # return render_template(
    #     "confirm.html",
    #     ipfs_pdf_url=final_ipfs_link,
    #     cert_id=next_cert_id,
    #     timestamp=date
    # )

if __name__ == "__main__":
    #app.run(debug=True, use_reloader=False)
    #app.run()
    app.run()
    #app.run(debug=True)