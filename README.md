# NHAI AI Toll System Dashboard 🚗💳

An advanced AI-powered smart toll monitoring and deduction system designed to process vehicle license plates in real-time, deduct toll fees, and alert operators of suspicious activity.

## Features ✨
- **AI Plate Recognition**: Uses OpenCV and PyTesseract for Optical Character Recognition (OCR) to detect and read license plates from images.
- **Dynamic Preprocessing**: Implements a 5-stage sequential processing engine (Otsu, Adaptive, Binary, etc.) to robustly read plates under various conditions.
- **Fuzzy Matching**: Intelligently autocorrects minor OCR errors by fuzzy matching the reading against a database of known registered vehicles.
- **Real-Time Toll Deduction**: Automatically deducts toll amounts (₹100) from the user's wallet.
- **Fraud Detection**: Flags vehicles passing toll nodes anomalously or with invalid registrations/pending fines.
- **Wallet Recharge**: Built-in functionality to recharge balances and instantly send automated email receipts.

## How to Run 🚀

### 1. Install Dependencies
Ensure you have Python installed, then install the required libraries:
```bash
pip install streamlit opencv-python pytesseract pandas ultralytics
```

### 2. Install Tesseract OCR
You must install the Tesseract OCR executable on your machine.
- For Windows: Download and install from [UB-Mannheim's Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki).
- By default, the script expects Tesseract to be installed at: `C:\Program Files\Tesseract-OCR\tesseract.exe`. (Modify this path in `core.py` if yours differs).

### 3. Launch the Application
Run the Streamlit server from your terminal:
```bash
streamlit run app.py
```

## Structure 📂
- `app.py`: The main Streamlit dashboard application.
- `core.py`: The backend AI engine handling OpenCV filtering, Tesseract OCR extraction, and email dispatching.
- `vehicles.json`: A local JSON database acting as the primary data store for registered vehicles and their wallet balances.
- `ai_toll.py`: A standalone debugging script to test the OCR engine on local images.
