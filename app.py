
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

def add_record(location, record_type, boxes):
    sheet = connect_sheet()
    now = datetime.now()

    row = [
        now.strftime("%d/%m/%Y"),
        now.strftime("%H:%M:%S"),
        location,
        record_type,
        boxes
    ]

    sheet.append_row(row)

def load_records():
    sheet = connect_sheet()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def delete_record(row_number):
    sheet = connect_sheet()
    sheet.delete_rows(row_number)

st.title("🚚 NP Delivery Tracker")

record_type = st.selectbox("Record Type", ["Pick up", "Drop off"])

if "boxes" not in st.session_state:
    st.session_state.boxes = 0

st.session_state.boxes = int(st.session_state.boxes)

st.subheader("Number of Boxes")

boxes = st.number_input(
    "Boxes",
    main_value = 0,
    step = 1,
    value=int(st.session_state.boxes),
    key="boxes_input"
)

st.session_state.boxes = int(boxes)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

with col1:
    if st.button("-10"):
        st.session_state.boxes = max(0, int(st.session_state.boxes) - 10)
        set.rerun()

with col2:
    if st.button("-5"):
        st.session_state.boxes = max(0,int(st.session_state.boxes) - 5)
        set.rerun()

with col3:
    if st.button("-1"):
        st.session_state.boxes = max(0, int(st.session_state.boxes) - 1)
        set.rerun()

with col4:
    if st.button("Reset"):
        st.session_state.boxes = 0
        set.rerun()

with col5:
    if st.button("+1"):
        st.session_state.boxes = int(st.session_state.boxes) + 1
        set.rerun()

with col6:
    if st.button("+2"):
        st.session_state.boxes = int(st.session_state.boxes) + 2
        set.rerun()

with col7:
    if st.button("+5"):
        st.session_state.boxes = int(st.session_state.boxes) + 5
        set.rerun()

boxes = st.session_state.boxes

st.write("Tap a location to record current time:")

for location in LOCATIONS:
    if st.button(location, use_container_width=True):
        add_record(location, record_type, boxes)
        st.success(f"Recorded: {location}")

st.divider()

st.subheader("Records")

try:
    df = load_records()

    if df.empty:
        st.info("No records yet.")
    else:
        df_display = df.copy()
        df_display.insert(0, "Sheet Row", range(2, len(df_display) + 2))

        st.dataframe(df_display, use_container_width=True)

        st.subheader("Delete a record")

        row_to_delete = st.selectbox(
            "Select the Sheet Row to delete",
            df_display["Sheet Row"].tolist(),
            format_func=lambda x: f"Row {x} - {df_display[df_display['Sheet Row'] == x]['Date'].values[0]} "
                                  f"{df_display[df_display['Sheet Row'] == x]['Time'].values[0]} "
                                  f"{df_display[df_display['Sheet Row'] == x]['Location'].values[0]} "
                                  f"{df_display[df_display['Sheet Row'] == x]['Type'].values[0]}"
        )

        confirm_delete = st.checkbox("I confirm I want to delete this record")

        if st.button("Delete selected record", use_container_width=True):
            if confirm_delete:
                delete_record(row_to_delete)
                st.success("Record deleted.")
                st.rerun()
            else:
                st.warning("Please tick the confirmation box first.")

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
