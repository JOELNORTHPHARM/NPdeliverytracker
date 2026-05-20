
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

def add_record(location, record_type, current_boxes):
    sheet = connect_sheet()
    now = datetime.now()

    row = [
        now.strftime("%d/%m/%Y"),
        now.strftime("%H:%M:%S"),
        location,
        record_type,
        current_boxes
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

def change_boxes(amount):
    current = int(st.session_state.get("boxes", 0))
    st.session_state.boxes = max(0, current + amount)


def reset_boxes():
    st.session_state.boxes = 0


if "boxes" not in st.session_state:
    st.session_state.boxes = 0

st.write("Select location:")

selected_location = st.selectbox(
    "Location",
    LOCATIONS
)

current_boxes = st.number_input(
    "Number of Boxes",
    min_value=0,
    step=1,
    value=0
)

if st.button("Record", use_container_width=True, type="primary"):
    add_record(selected_location, record_type, current_boxes)
    st.success(
        f"{record_type} recorded at {selected_location} ({current_boxes} boxes)"
    )

st.divider()

st.subheader("Records")

if st.button("Load / Refresh Records", use_container_width=True):
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
                format_func=lambda x: f"Row {x} - "
                                      f"{df_display[df_display['Sheet Row'] == x]['Date'].values[0]} "
                                      f"{df_display[df_display['Sheet Row'] == x]['Time'].values[0]} "
                                      f"{df_display[df_display['Sheet Row'] == x]['Location'].values[0]} "
                                      f"{df_display[df_display['Sheet Row'] == x]['Type'].values[0]}"
            )

            confirm_delete = st.checkbox("I confirm I want to delete this record")

            if st.button("Delete selected record", use_container_width=True):
                if confirm_delete:
                    delete_record(row_to_delete)
                    st.success("Record deleted.")
                else:
                    st.warning("Please tick the confirmation box first.")

            csv = df_display.to_csv(index=False).encode("utf-8-sig")

            st.download_button(
                "Download CSV",
                csv,
                "np_delivery_tracker.csv",
                "text/csv",
                use_container_width=True
            )

    except Exception as e:
        st.error("Could not load records.")
        st.exception(e)

else:
    st.info("Tap 'Load / Refresh Records' only when you need to view, delete, or export records.")


