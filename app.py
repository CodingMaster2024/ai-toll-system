import streamlit as st
import json
import os
from core import extract_plate, process_vehicle, send_sms, send_email
import pandas as pd
import base64
import time
import random
import uuid

st.set_page_config(page_title="NHAI AI Toll System", layout="wide")

# ---------------- SESSION STATE ----------------
if "logs" not in st.session_state:
    st.session_state.logs = []

if "violations" not in st.session_state:
    st.session_state.violations = []

if "last_seen" not in st.session_state:
    st.session_state.last_seen = {}

# ---------------- BACKGROUND ----------------
with open("bg.jpg", "rb") as f:
    bg = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-image: linear-gradient(
        rgba(0, 0, 0, 0.8),
        rgba(0, 0, 0, 0.8)
    ),
    url("data:image/jpg;base64,{bg}");
    background-size: cover;
}}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
with open("nhai.png", "rb") as f:
    logo = base64.b64encode(f.read()).decode()

st.markdown(f"""
<div style='text-align: center;'>

<img src="data:image/png;base64,{logo}" width="300">

<h2>NHAI - Not Just Roads, Building A Nation</h2>
<h1>AI Toll System Dashboard</h1>
<p>Smart Toll | AI Detection | Real-Time Processing</p>

</div>
""", unsafe_allow_html=True)

# ---------------- LIVE STATUS ----------------
current_time_str = time.strftime("%H:%M")
colA, colB = st.columns(2)
colA.metric("🕒 System Time", current_time_str)
colB.metric("System Mode", "Active")

# ---------------- LOAD DB ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vehicles.json")

def load_db():
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- TABS ----------------
tab1, tab2 = st.tabs(["🚗 Vehicle Processing", "💳 Wallet Recharge"])

# =========================
# 🚧 TOLL SYSTEM
# =========================
with tab1:

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📷 Vehicle Detection")

        uploaded = st.file_uploader("Upload Vehicle Image", type=["jpg", "png", "jpeg"])

        if uploaded:
            file_bytes = uploaded.getvalue()
            file_hash = hash(file_bytes)

            st.image(file_bytes, width="stretch")

            if "last_file_hash" not in st.session_state:
                st.session_state.last_file_hash = None
                st.session_state.last_plate = None
                st.session_state.last_result = None
                st.session_state.last_txn_id = None

            if st.session_state.last_file_hash != file_hash:
                st.session_state.last_file_hash = file_hash
                
                temp_filename = f"temp_{uuid.uuid4().hex[:8]}.jpg"
                with open(temp_filename, "wb") as f:
                    f.write(file_bytes)
                
                try:
                    plate = extract_plate(temp_filename)
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                        
                st.session_state.last_plate = plate
                
                result = process_vehicle(plate)
                st.session_state.last_result = result

                node_id = f"TOLL-{random.randint(101,105)}"
                current_time = time.time()
                fraud_flag = "None"
                
                if plate in st.session_state.last_seen:
                    last_time, last_node = st.session_state.last_seen[plate]
                    time_diff = current_time - last_time
                    if time_diff < 30 and last_node != node_id:
                        fraud_flag = "Anomalous Movement"
                st.session_state.last_seen[plate] = (current_time, node_id)

                txn_id = str(uuid.uuid4())[:8]
                st.session_state.last_txn_id = txn_id

                st.session_state.logs.append({
                    "Txn_ID": txn_id,
                    "Vehicle": plate,
                    "Time": time.strftime("%H:%M:%S"),
                    "Node": node_id,
                    "Event": "PASS",
                    "Fraud": fraud_flag
                })

                if result["status"] == "fines":
                    st.session_state.violations.append({"Txn_ID": txn_id, "Vehicle": plate, "Time": time.strftime("%H:%M:%S"), "Type": "Pending Fines"})
                elif result["status"] == "low_balance":
                    st.session_state.violations.append({"Txn_ID": txn_id, "Vehicle": plate, "Time": time.strftime("%H:%M:%S"), "Type": "Insufficient Balance"})
                elif result["status"] == "invalid":
                    st.session_state.violations.append({"Txn_ID": txn_id, "Vehicle": plate, "Time": time.strftime("%H:%M:%S"), "Type": "Invalid Registration"})
                elif result["status"] == "not_registered":
                    st.session_state.violations.append({"Txn_ID": txn_id, "Vehicle": plate, "Time": time.strftime("%H:%M:%S"), "Type": "Unregistered Vehicle"})

            # Render UI from cached state
            plate = st.session_state.last_plate
            result = st.session_state.last_result

            st.markdown(f"""
<div style='font-size:22px; padding:10px; background:#111827; border-radius:10px; text-align:center;'>
Detected Plate: <b>{plate}</b>
</div>
""", unsafe_allow_html=True)

            if result["status"] == "success":
                st.success(f"✅ Toll Deducted  \n\n👤 {result['owner']}  \n💰 ₹{result['balance']}")
            elif result["status"] == "fines":
                st.warning("⚠️ Violation: Pending Fines")
            elif result["status"] == "low_balance":
                st.error("🚫 Violation: Insufficient Balance")
            elif result["status"] == "invalid":
                st.error("🚫 Violation: Invalid Registration")
            else:
                st.error("🚫 Violation: Unregistered Vehicle")

    with col2:
        st.subheader("🛰️ NHAI Central Monitoring")

        total_vehicles = len(st.session_state.logs)
        total_violations = len(st.session_state.violations)
        estimated_revenue = total_vehicles * 100

        st.metric("Vehicles Processed", total_vehicles)
        st.metric("Total Revenue (₹)", estimated_revenue)
        st.metric("Violations Detected", total_violations)
        st.metric("Active Toll Nodes", 5)

# =========================
# 💳 RECHARGE
# =========================
with tab2:

    st.subheader("💳 Recharge Wallet")

    vehicles = load_db()

    col1, col2 = st.columns(2)

    with col1:
        plate = st.text_input("Vehicle Number")

    with col2:
        amount = st.number_input("Amount", min_value=1, step=50)

    if st.button("Recharge Now"):
        if plate in vehicles:
            vehicles[plate]["balance"] += amount
            save_db(vehicles)

            new_balance = vehicles[plate]["balance"]
            to_email  = vehicles[plate].get("email", "")

            if to_email:
                plain = (
                    f"NHAI FastToll — Wallet Recharge\n"
                    f"Vehicle : {plate}\n"
                    f"Recharged: Rs.{amount}\n"
                    f"New Balance: Rs.{new_balance}\n"
                    f"Time    : {time.strftime('%d %b %Y, %H:%M:%S')}"
                )
                html = f"""
<html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;">
<div style="max-width:460px;margin:auto;background:#1e293b;border-radius:14px;
            padding:28px;border:1px solid #334155;">
  <h2 style="color:#38bdf8;margin-top:0;">NHAI FastToll AI</h2>
  <p style="color:#94a3b8;margin-top:-12px;font-size:13px;">Wallet Recharge Confirmation</p>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:7px 0;color:#94a3b8;">Vehicle</td>
        <td style="text-align:right;font-weight:bold;font-family:monospace;
                   color:#f1f5f9;font-size:15px;">{plate}</td></tr>
    <tr><td style="padding:7px 0;color:#94a3b8;">Amount Recharged</td>
        <td style="text-align:right;font-weight:bold;color:#4ade80;">+Rs.{amount}</td></tr>
    <tr><td style="padding:7px 0;color:#94a3b8;">New Balance</td>
        <td style="text-align:right;font-weight:bold;color:#f1f5f9;">Rs.{new_balance}</td></tr>
    <tr><td style="padding:7px 0;color:#94a3b8;">Time</td>
        <td style="text-align:right;color:#f1f5f9;font-size:12px;">
            {time.strftime('%d %b %Y, %H:%M:%S')}</td></tr>
  </table>
  <p style="color:#475569;font-size:11px;margin-bottom:0;text-align:center;">
      NHAI FastToll AI — Automated Toll System</p>
</div></body></html>"""
                send_email(to_email, f"💳 NHAI FastToll – Wallet Recharged for {plate}", plain, html)

            st.success(f"Recharge Successful | Balance: ₹{new_balance}")

            txn_id = str(uuid.uuid4())[:8]

            st.session_state.logs.append({
                "Txn_ID": txn_id,
                "Vehicle": plate,
                "Time": time.strftime("%H:%M:%S"),
                "Node": "WALLET",
                "Event": "RECHARGE",
                "Fraud": "None"
            })

        else:
            st.error("Vehicle Not Found")

# =========================
# 📜 TRANSACTION LOG
# =========================
st.markdown("---")
st.subheader("🧾 Transaction Log")

df = pd.DataFrame(st.session_state.logs)
st.dataframe(df, width="stretch")

csv = df.to_csv(index=False).encode('utf-8')

st.download_button("⬇️ Download CSV", csv, "transactions.csv", "text/csv")

# =========================
# 🚫 VIOLATION LOG
# =========================
st.markdown("---")
st.subheader("🚫 Violation Log")

v_df = pd.DataFrame(st.session_state.violations)
st.dataframe(v_df, width="stretch")

# =========================
# ⚠️ FRAUD PANEL
# =========================
fraud_count = sum(
    1 for x in st.session_state.logs
    if x["Fraud"] != "None" and x["Event"] == "PASS"
)

st.metric("⚠️ Anomaly Alerts", fraud_count)