
import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="NP Delivery Tracker", page_icon="🚚", layout="centered")

LOCATIONS = [
    "Stuart Park Pharmacy",
    "DCC",
    "DCC Youth",
    "BCC",
    "Watch House",
    "Packing Facility",
    "Karama Pharmacy",
    "Northpharm RDH"
]

SHEET_NAME = "NP Delivery Tracker"

def connect_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scopes
    )

    client = gspread.authorize(credentials)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

def add_record(location, record_type):
    sheet = connect_sheet()
    now = datetime.now()

    row = [
        now.strftime("%d/%m/%Y"),
        now.strftime("%H:%M:%S"),
        location,
        record_type
    ]

    sheet.append_row(row)

def load_records():
    sheet = connect_sheet()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

st.title("🚚 NP Delivery Tracker")

record_type = st.selectbox("Record Type", ["Pick up", "Drop off"])

st.write("Tap a location to record current time:")

for location in LOCATIONS:
    if st.button(location, use_container_width=True):
        add_record(location, record_type)
        st.success(f"Recorded: {location}")

st.divider()

st.subheader("Records")

try:
    df = load_records()
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download CSV",
        csv,
        "np_delivery_tracker.csv",
        "text/csv",
        use_container_width=True
    )

except Exception as e:
    st.warning("No records yet, or Google Sheet is not connected.")
    st.error(e)
