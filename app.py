import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

st.set_page_config(
    page_title="NorthPharm Operations System",
    page_icon="🐢",
    layout="centered"
)

with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

if 'AuthenticationService.__init__' in st.session_state:
    del st.session_state['AuthenticationService.__init__']

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

SHEET_NAME = "NorthPharm Delivery Tracker"

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

@st.cache_resource
def get_cached_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scopes
    )
    return gspread.authorize(credentials)

def get_worksheet(sheet_name):
    client = get_cached_client()
    spreadsheet = client.open(SHEET_NAME)
    return spreadsheet.worksheet(sheet_name)

def connect_delivery_sheet():
    client = get_cached_client()
    return client.open(SHEET_NAME).sheet1

def add_delivery_record(location, record_type, boxes):
    sheet = connect_delivery_sheet()
    now = datetime.now(ZoneInfo("Australia/Darwin"))
    row = [
        now.strftime("%d/%m/%Y"),
        now.strftime("%H:%M:%S"),
        location,
        record_type,
        int(boxes)
    ]
    sheet.append_row(row)
    st.cache_data.clear()

@st.cache_data(ttl=60)
def load_delivery_records():
    sheet = connect_delivery_sheet()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def delete_delivery_record(row_number):
    sheet = connect_delivery_sheet()
    sheet.delete_rows(int(row_number))
    st.cache_data.clear()

@st.cache_data(ttl=60)
def load_inventory_items():
    sheet = get_worksheet("Inventory_Items")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

@st.cache_data(ttl=60)
def load_inventory_movements():
    sheet = get_worksheet("Inventory_Movements")
    rows = sheet.get_all_values()
    if not rows:
        return pd.DataFrame()
    headers = rows[0]
    seen = {}
    clean_headers = []
    for h in headers:
        if h == '':
            h = f'_empty_{len(seen)}'
        seen[h] = seen.get(h, 0) + 1
        if seen[h] > 1:
            h = f'{h}_{seen[h]}'
        clean_headers.append(h)
    return pd.DataFrame(rows[1:], columns=clean_headers)

@st.cache_data(ttl=60)
def update_inventory_item_qty(item_name, new_qty):
    sheet = get_worksheet("Inventory_Items")
    data = sheet.get_all_records()
    for i, row in enumerate(data):
        if row['Item'] == item_name:
            sheet.update_cell(i + 2, 3, new_qty)
            break
    st.cache_data.clear()

def add_inventory_movement(item_name, movement_type, qty, location, notes=""):
    sheet = get_worksheet("Inventory_Movements")
    now = datetime.now(ZoneInfo("Australia/Darwin"))
    row = [
        now.strftime("%d/%m/%Y"),
        now.strftime("%H:%M:%S"),
        item_name,
        movement_type,
        int(qty),
        location,
        notes
    ]
    sheet.append_row(row)
    st.cache_data.clear()

def process_inventory_action(item_name, action, qty, location, notes=""):
    items_df = load_inventory_items()
    item_row = items_df[items_df['Item'] == item_name]
    if item_row.empty:
        st.error(f"Item '{item_name}' not found.")
        return
    current_qty = int(item_row.iloc[0]['Quantity'])
    if action == "Dispatch":
        new_qty = current_qty - int(qty)
    elif action == "Receive":
        new_qty = current_qty + int(qty)
    else:
        st.error("Invalid action.")
        return
    if new_qty < 0:
        st.error(f"Insufficient stock.")
        return
    update_inventory_item_qty(item_name, new_qty)
    add_inventory_movement(item_name, action, qty, location, notes)

def add_new_inventory_item(item_name, category, initial_qty):
    sheet = get_worksheet("Inventory_Items")
    row = [item_name, category, int(initial_qty)]
    sheet.append_row(row)
    st.cache_data.clear()

def get_stock_status(qty):
    if qty <= 0:
        return "Out of Stock"
    elif qty <= 10:
        return "Low Stock"
    else:
        return "In Stock"

name, auth_status, username = authenticator.login(
    fields={
        'Form name': 'NorthPharm Login',
        'Username': 'Username',
        'Password': 'Password',
        'Login': 'Login'
    }
)

if auth_status is False:
    st.error("Username/password is incorrect")
elif auth_status is None:
    st.warning("Please enter your username and password")
elif auth_status:
    authenticator.logout("Logout", "sidebar")
    role = config["credentials"]["usernames"].get(username.lower(), {}).get("role", "user")
    st.sidebar.title(f"Welcome, {name}!")
    st.sidebar.markdown(f"**Role:** {role.capitalize()}")
    page = st.sidebar.radio("Navigate", ["Delivery Tracker", "Inventory"])
    if page == "Delivery Tracker":
        st.title("Delivery Tracker")
        with st.expander("Add Delivery Record", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                location = st.selectbox("Location", LOCATIONS)
            with col2:
                record_type = st.selectbox("Type", ["Delivery", "Pickup"])
            with col3:
                boxes = st.number_input("Boxes", min_value=1, value=1)
            if st.button("Submit Record"):
                add_delivery_record(location, record_type, boxes)
                st.success("Record added!")
                st.rerun()
        st.subheader("Records")
        df = load_delivery_records()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            if role == "admin":
                with st.expander("Delete Record (Admin Only)"):
                    row_to_delete = st.number_input("Row number", min_value=1, value=1)
                    if st.button("Delete Row"):
                        delete_delivery_record(row_to_delete + 1)
                        st.success(f"Row {row_to_delete} deleted.")
                        st.rerun()
        else:
            st.info("No records found.")
    elif page == "Inventory":
        st.title("Inventory Management")
        tab1, tab2, tab3 = st.tabs(["Stock Overview", "Add Movement", "New Item"])
        with tab1:
            items_df = load_inventory_items()
            if not items_df.empty:
                items_df['Status'] = items_df['Quantity'].apply(lambda x: get_stock_status(int(x)))
                st.dataframe(items_df, use_container_width=True)
            else:
                st.info("No inventory items found.")
        with tab2:
            items_df = load_inventory_items()
            if not items_df.empty:
                item_names = items_df['Item'].tolist()
                col1, col2 = st.columns(2)
                with col1:
                    selected_item = st.selectbox("Item", item_names)
                    action = st.selectbox("Action", ["Dispatch", "Receive"])
                with col2:
                    qty = st.number_input("Quantity", min_value=1, value=1)
                    location = st.selectbox("Location", LOCATIONS)
                notes = st.text_input("Notes (optional)")
                if st.button("Submit Movement"):
                    process_inventory_action(selected_item, action, qty, location, notes)
                    st.success("Movement recorded!")
                    st.rerun()
            else:
                st.warning("No items in inventory yet.")
        with tab3:
            if role == "admin":
                new_item = st.text_input("Item Name")
                new_category = st.text_input("Category")
                new_qty = st.number_input("Initial Quantity", min_value=0, value=0)
                if st.button("Add Item"):
                    if new_item:
                        add_new_inventory_item(new_item, new_category, new_qty)
                        st.success(f"'{new_item}' added.")
                        st.rerun()
                    else:
                        st.error("Item name cannot be empty.")
            else:
                st.info("Admin access required.")
