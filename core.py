import cv2
import pytesseract
import re
import json
import os
import smtplib
import time as _time
import threading
from email.message import EmailMessage

# ---------------- CONFIG ----------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TOLL_AMOUNT = 100

SENDER_EMAIL    = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"   # Gmail App Password

# ---------------- LOAD DB ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vehicles.json")

def load_db():
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

import difflib

# ---------------- OCR FUNCTION (NLP)----------------
def extract_plate(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return "ERROR"

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_filtered = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(gray_filtered, 50, 200)

    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plate_img = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.018 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(c)
            plate_img = image[y:y+h, x:x+w]
            break

    # fallback: if no contour found, assume entire image is the plate
    if plate_img is None or plate_img.size == 0:
        plate_img = image

    def do_ocr(img):
        config = r'--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(img, config=config)
        return re.sub(r'[^A-Z0-9]', '', text.upper())

    # Base preprocessing for plate
    gray_plate = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    gray_plate = cv2.resize(gray_plate, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # Strategy 1: Otsu
    gray_blur = cv2.bilateralFilter(gray_plate, 11, 20, 20)
    _, thresh_otsu = cv2.threshold(gray_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    plate_text = do_ocr(thresh_otsu)

    # Strategy 2: Simple threshold
    if len(plate_text) < 6:
        _, thresh_simple = cv2.threshold(gray_plate, 150, 255, cv2.THRESH_BINARY)
        plate_text = do_ocr(thresh_simple)

    # Strategy 3: Inverted threshold
    if len(plate_text) < 6:
        _, thresh_simple = cv2.threshold(gray_plate, 150, 255, cv2.THRESH_BINARY)
        plate_text = do_ocr(cv2.bitwise_not(thresh_simple))
        
    # Strategy 4: Adaptive threshold
    if len(plate_text) < 6:
        adaptive = cv2.adaptiveThreshold(gray_plate, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 15)
        plate_text = do_ocr(adaptive)

    # Strategy 5: Raw grayscale
    if len(plate_text) < 6:
        plate_text = do_ocr(gray_plate)

    if len(plate_text) < 6:
        return "UNKNOWN"

    # Fuzzy matching to fix minor OCR typos (like O vs 0, 8 vs B, G vs 0)
    vehicles = load_db()
    known_plates = list(vehicles.keys())
    if plate_text not in known_plates:
        matches = difflib.get_close_matches(plate_text, known_plates, n=1, cutoff=0.7)
        if matches:
            plate_text = matches[0]

    return plate_text

# ---------------- EMAIL FUNCTION ----------------
def send_email(to_email, subject, plain_body, html_body=None):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = to_email
        msg.set_content(plain_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print(f"[EMAIL] Sent -> {to_email}")
    except Exception as e:
        print(f"[EMAIL] Failed: {e}")

# keep old name so app.py recharge call still works
def send_sms(to_number, message):
    pass   # SMS replaced by email — no-op

# ---------------- DECISION ENGINE ----------------
def process_vehicle(plate_text):
    vehicles = load_db()

    if plate_text not in vehicles:
        return {"status": "not_registered"}

    v = vehicles[plate_text]

    if v["status"] != "valid":
        return {"status": "invalid"}

    if v["fines"] > 0:
        return {
            "status": "fines",
            "amount": v["fines"]
        }

    if v["balance"] < TOLL_AMOUNT:
        return {"status": "low_balance"}

    # SUCCESS CASE
    v["balance"] -= TOLL_AMOUNT
    save_db(vehicles)

    to_email = v.get("email", "")
    if to_email:
        plain = (
            f"NHAI FastToll AI — Receipt\n"
            f"Vehicle : {plate_text}\n"
            f"Owner   : {v['owner']}\n"
            f"Deducted: Rs.{TOLL_AMOUNT}\n"
            f"Balance : Rs.{v['balance']}\n"
            f"Time    : {_time.strftime('%d %b %Y, %H:%M:%S')}"
        )
        html = f"""
<html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;">
<div style="max-width:460px;margin:auto;background:#1e293b;border-radius:14px;
            padding:28px;border:1px solid #334155;">
  <h2 style="color:#38bdf8;margin-top:0;">NHAI FastToll AI</h2>
  <p style="color:#94a3b8;margin-top:-12px;font-size:13px;">Automated Toll Receipt</p>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:7px 0;color:#94a3b8;">Vehicle</td>
        <td style="text-align:right;font-weight:bold;font-family:monospace;
                   color:#f1f5f9;font-size:15px;">{plate_text}</td></tr>
    <tr><td style="padding:7px 0;color:#94a3b8;">Owner</td>
        <td style="text-align:right;color:#f1f5f9;">{v['owner']}</td></tr>
    <tr><td style="padding:7px 0;color:#94a3b8;">Toll Deducted</td>
        <td style="text-align:right;font-weight:bold;color:#f87171;">-Rs.{TOLL_AMOUNT}</td></tr>
    <tr><td style="padding:7px 0;color:#94a3b8;">Remaining Balance</td>
        <td style="text-align:right;font-weight:bold;color:#4ade80;">Rs.{v['balance']}</td></tr>
    <tr><td style="padding:7px 0;color:#94a3b8;">Time</td>
        <td style="text-align:right;color:#f1f5f9;font-size:12px;">
            {_time.strftime('%d %b %Y, %H:%M:%S')}</td></tr>
  </table>
  <p style="color:#475569;font-size:11px;margin-bottom:0;text-align:center;">
      NHAI FastToll AI — Automated Toll System</p>
</div></body></html>"""
        threading.Thread(target=send_email,
                         args=(to_email, f"✅ NHAI FastToll – Toll for {plate_text}", plain, html),
                         daemon=True).start()

    return {
        "status": "success",
        "owner": v["owner"],
        "balance": v["balance"]
    }