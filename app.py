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

def get_client():
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
    client = get_client()
    spreadsheet = client.open(SHEET_NAME)
    return spreadsheet.worksheet(sheet_name)


def connect_delivery_sheet():
    client = get_client()
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


def load_delivery_records():
    sheet = connect_delivery_sheet()
    data = sheet.get_all_records()
    return pd.DataFrame(data)


def delete_delivery_record(row_number):
    sheet = connect_delivery_sheet()
    sheet.delete_rows(int(row_number))


def load_inventory_items():
    sheet = get_worksheet("Inventory_Items")
    data = sheet.get_all_records()
    return pd.DataFrame(data)


def load_inventory_movements():
    sheet = get_worksheet("Inventory_Movements")
    data = sheet.get_all_records()
    return pd.DataFrame(data)


def update_inventory_item_qty(item_id, new_qty):
    sheet = get_worksheet("Inventory_Items")
    records = sheet.get_all_records()

    for index, row in enumerate(records, start=2):
        if row["Item ID"] == item_id:
            sheet.update_cell(index, 6, int(new_qty))
            return True

    return False


def add_inventory_movement(user, item, action, qty_change, balance_after, note):
    sheet = get_worksheet("Inventory_Movements")
    now = datetime.now(ZoneInfo("Australia/Darwin"))

    row = [
        now.strftime("%d/%m/%Y"),
        now.strftime("%H:%M:%S"),
        user,
        item["Item ID"],
        item["Item Name"],
        item["Size"],
        action,
        int(qty_change),
        int(balance_after),
        note
    ]

    sheet.append_row(row)


def process_inventory_action(user, item_id, action, qty, note=""):
    items = load_inventory_items()

    if items.empty:
        st.error("Inventory_Items sheet is empty.")
        return

    item_row = items[items["Item ID"] == item_id]

    if item_row.empty:
        st.error("Selected item was not found.")
        return

    item = item_row.iloc[0]
    current_qty = int(item["Current Qty"])
    qty = int(qty)

    if action == "Take Stock":
        new_qty = max(0, current_qty - qty)
        qty_change = new_qty - current_qty

    elif action == "Add Stock":
        new_qty = current_qty + qty
        qty_change = qty

    elif action == "Stocktake Adjustment":
        new_qty = qty
        qty_change = new_qty - current_qty

    else:
        st.error("Invalid inventory action.")
        return

    updated = update_inventory_item_qty(item_id, new_qty)

    if not updated:
        st.error("Could not update inventory quantity.")
        return

    add_inventory_movement(
        user=user,
        item=item,
        action=action,
        qty_change=qty_change,
        balance_after=new_qty,
        note=note
    )


def add_new_inventory_item(category, item_name, size, unit, initial_qty, low_stock_level):
    sheet = get_worksheet("Inventory_Items")
    items = load_inventory_items()

    item_id = category.upper().replace(" ", "_") + "_" + size.upper().replace(" ", "_")

    if not items.empty and item_id in items["Item ID"].values:
        st.error("This item already exists.")
        return

    row = [
        item_id,
        category,
        item_name,
        size,
        unit,
        int(initial_qty),
        int(low_stock_level),
        True
    ]

    sheet.append_row(row)
    st.success("New item added.")


def get_stock_status(row):
    current_qty = int(row["Current Qty"])
    low_level = int(row["Low Stock Level"])

    if current_qty <= 0:
        return "Out of Stock"
    if current_qty <= low_level:
        return "Low Stock"
    return "OK"

authenticator.login()

auth_status = st.session_state.get("authentication_status")

if auth_status:
    username = st.session_state.get("username", "Unknown")
    role = config["credentials"]["usernames"].get(username, {}).get("role", "user")

    authenticator.logout("logout", "main")

elif auth_status is False:
    st.error("Username/password is incorrect.")
    st.stop()

elif auth_status is None:
    st.warning("Please enter your username and password")
    st.stop()


st.caption(f"Logged in as: {username} ({role})")


module = st.sidebar.radio(
    "Module",
    ["Delivery Tracker", "Inventory Management"]
)


if module == "Delivery Tracker":
    st.title("🚚 NorthPharm Delivery Tracker")

    record_type = st.selectbox(
        "Record Type",
        ["Pick up", "Drop off"]
    )

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
        add_delivery_record(selected_location, record_type, current_boxes)
        st.success(
            f"{record_type} recorded at {selected_location} ({current_boxes} boxes)"
        )

    st.divider()

    st.subheader("Records")

    if "show_delivery_records" not in st.session_state:
        st.session_state.show_delivery_records = False

    if st.button("Load / Refresh Records", use_container_width=True):
        st.session_state.show_delivery_records = True

    if st.session_state.show_delivery_records:
        try:
            df = load_delivery_records()

            if df.empty:
                st.info("No records yet.")
            else:
                df_display = df.copy()
                df_display.insert(0, "Sheet Row", range(2, len(df_display) + 2))

                st.dataframe(df_display, use_container_width=True)

                row_to_delete = st.selectbox(
                    "Delete record",
                    df_display["Sheet Row"].tolist(),
                    format_func=lambda x: f"Row {x} - "
                                          f"{df_display[df_display['Sheet Row'] == x]['Date'].values[0]} "
                                          f"{df_display[df_display['Sheet Row'] == x]['Time'].values[0]} "
                                          f"{df_display[df_display['Sheet Row'] == x]['Location'].values[0]}"
                )

                if role == "admin":
                    if st.button("Delete selected record", use_container_width=True):
                        delete_delivery_record(row_to_delete)
                        st.success("Record deleted.")
                        st.session_state.show_delivery_records = False
                else:
                    st.info("Only admin users can delete records.")

                csv = df_display.to_csv(index=False).encode("utf-8-sig")

                st.download_button(
                    "Download CSV",
                    csv,
                    "np_delivery_tracker.csv",
                    "text/csv",
                    use_container_width=True
                )

        except Exception as e:
            st.error("Could not load delivery records.")
            st.exception(e)


elif module == "Inventory Management":
    st.title("📦 NorthPharm Stock Level Management")

    inventory_menu = st.selectbox(
        "Inventory Function",
        [
            "Current Stock",
            "Take Stock",
            "Add Stock",
            "Stocktake Adjustment",
            "Add New Item",
            "Movement History"
        ]
    )

    try:
        items_df = load_inventory_items()

        if items_df.empty:
            st.warning("Inventory_Items sheet is empty.")
            st.stop()

        active_items = items_df[
            items_df["Active"].astype(str).str.upper().isin(["TRUE", "YES", "1"])
        ].copy()

        if inventory_menu == "Current Stock":
            st.subheader("Current Stock")

            report = active_items.copy()
            report["Status"] = report.apply(get_stock_status, axis=1)

            st.dataframe(report, use_container_width=True)

            csv = report.to_csv(index=False).encode("utf-8-sig")

            st.download_button(
                "Download Stock Report",
                csv,
                "current_stock_report.csv",
                "text/csv",
                use_container_width=True
            )

        elif inventory_menu in ["Take Stock", "Add Stock", "Stocktake Adjustment"]:
            st.subheader(inventory_menu)

            selected_item_id = st.selectbox(
                "Select Item",
                active_items["Item ID"].tolist(),
                format_func=lambda x: (
                    f"{active_items[active_items['Item ID'] == x]['Item Name'].values[0]} - "
                    f"{active_items[active_items['Item ID'] == x]['Size'].values[0]} "
                    f"(Current: {active_items[active_items['Item ID'] == x]['Current Qty'].values[0]})"
                )
            )

            qty_label = (
                "Actual counted quantity"
                if inventory_menu == "Stocktake Adjustment"
                else "Quantity"
            )

            qty = st.number_input(
                qty_label,
                min_value=0,
                step=1,
                value=0
            )

            note = st.text_input("Note", value="")

            if st.button(inventory_menu, use_container_width=True, type="primary"):
                process_inventory_action(
                    user=username,
                    item_id=selected_item_id,
                    action=inventory_menu,
                    qty=int(qty),
                    note=note
                )
                st.success("Inventory updated successfully.")

        elif inventory_menu == "Add New Item":
            st.subheader("Add New Item")

            if role != "admin":
                st.warning("Only admin users can add new items.")
            else:
                category = st.text_input("Category")
                item_name = st.text_input("Item Name")
                size = st.text_input("Size")
                unit = st.text_input("Unit", value="pcs")
                initial_qty = st.number_input(
                    "Initial Quantity",
                    min_value=0,
                    step=1,
                    value=0
                )
                low_stock_level = st.number_input(
                    "Low Stock Level",
                    min_value=0,
                    step=1,
                    value=5
                )

                if st.button("Add Item", use_container_width=True, type="primary"):
                    if category and item_name and size:
                        add_new_inventory_item(
                            category=category,
                            item_name=item_name,
                            size=size,
                            unit=unit,
                            initial_qty=int(initial_qty),
                            low_stock_level=int(low_stock_level)
                        )
                    else:
                        st.warning("Please fill Category, Item Name, and Size.")

        elif inventory_menu == "Movement History":
            st.subheader("Movement History")

            movements = load_inventory_movements()

            if movements.empty:
                st.info("No movement records yet.")
            else:
                st.dataframe(movements, use_container_width=True)

                csv = movements.to_csv(index=False).encode("utf-8-sig")

                st.download_button(
                    "Download Movement History",
                    csv,
                    "inventory_movement_history.csv",
                    "text/csv",
                    use_container_width=True
                )

    except Exception as e:
        st.error("Could not load inventory module.")
        st.exception(e)
