# app.py

import streamlit as st
import pandas as pd
import io
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Advanced Reconciliation Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- HELPER FUNCTIONS ---

@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV file for downloading."""
    return df.to_csv(index=False).encode('utf-8')

def extract_code_from_ref(reference):
    """Finds the last occurrence of the pattern 'CODE/NUMBER' in a string."""
    if not isinstance(reference, str): return ""
    pattern = r'[A-Z0-9&_-]+/\d+'
    matches = re.findall(pattern, reference)
    return matches[-1] if matches else ""

def generate_payment_schedule(contract_row):
    """Generates a month-by-month payment schedule from a contract's details."""
    try:
        start_date = pd.to_datetime(contract_row['Start Date'], dayfirst=True)
        end_date = pd.to_datetime(contract_row['End Date'], dayfirst=True)
        installment_amount = contract_row['Installment Amount']
        monthly_dates = pd.date_range(start=start_date, end=end_date, freq='MS')
        if monthly_dates.empty: return pd.DataFrame()
        schedule_df = pd.DataFrame({
            'Payment Month': monthly_dates.strftime('%B %Y'),
            'PaymentDate': monthly_dates,
            'Amount': installment_amount
        })
        return schedule_df
    except (ValueError, TypeError):
        return pd.DataFrame()

# --- SESSION STATE INITIALIZATION ---
if 'df1_processed' not in st.session_state: st.session_state.df1_processed = None
if 'df2_final' not in st.session_state: st.session_state.df2_final = None

# --- APP TITLE ---
st.title("📊 Advanced Contract & Transaction Reconciliation Dashboard")
st.markdown("A tool to process, compare, and analyze tenancy contracts and transactions.")

# --- TABS ---
tab_upload, tab_reco, tab_schedule, tab_data_view = st.tabs([
    "📂 **Step 1: File Upload**",
    "📈 **Step 2: Reconciliation**",
    "📅 **Step 3: Payment Schedule**",
    "📄 **Step 4: View Full Data**"
])

# --- TAB 1: FILE UPLOAD (No Changes) ---
with tab_upload:
    # ... code for tab 1 remains the same ...
    st.header("Upload Your Files Here")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.subheader("Tenancy Contracts File")
        uploaded_file_1 = st.file_uploader("Upload the main contract file.", type="xlsx", key="contracts")
        if uploaded_file_1:
            try:
                df1 = pd.read_excel(uploaded_file_1, engine='openpyxl')
                cols_1 = ['Tenants', 'Contract Reference', 'Start Date', 'End Date', 'No. of Cheques', 'Installment Amount', 'Contractual period (months)', 'Months Per Cheque', 'Rent As per Contract', 'Service as per Contract']
                missing_cols_1 = [col for col in cols_1 if col not in df1.columns]
                if not missing_cols_1:
                    df1_p = df1[cols_1].copy()
                    df1_p['Total Value'] = df1_p['Rent As per Contract'].fillna(0) + df1_p['Service as per Contract'].fillna(0)
                    for col in ['Start Date', 'End Date']:
                        df1_p[col] = pd.to_datetime(df1_p[col], errors='coerce').dt.strftime('%d-%m-%Y').fillna('')
                    df1_p['Contract Code'] = df1_p['Contract Reference'].apply(extract_code_from_ref)
                    st.session_state.df1_processed = df1_p
                    st.success(f"✅ Contract file processed successfully! Found {len(df1_p)} records.")
                else:
                    st.error(f"Contract file missing columns: {', '.join(missing_cols_1)}")
            except Exception as e: st.error(f"Error processing contract file: {e}")
    with col2:
        st.subheader("Transaction Log File")
        uploaded_file_2 = st.file_uploader("Upload the invoice transaction log.", type="xlsx", key="transactions")
        if uploaded_file_2:
            try:
                df2 = pd.read_excel(uploaded_file_2, engine='openpyxl')
                cols_2 = ['Date', 'Transaction Type', 'No.', 'Name', 'Amount']
                missing_cols_2 = [col for col in cols_2 if col not in df2.columns]
                if not missing_cols_2:
                    df2_inv = df2[df2['Transaction Type'].str.lower() == 'invoice'].copy()
                    df2_inv['Contract Code'] = df2_inv['No.'].apply(extract_code_from_ref)
                    df2_inv['Date'] = pd.to_datetime(df2_inv['Date'], errors='coerce').dt.strftime('%d-%m-%Y').fillna('')
                    st.session_state.df2_final = df2_inv[['Date', 'Name', 'No.', 'Contract Code', 'Amount']]
                    st.success(f"✅ Transaction log processed successfully! Found {len(df2_inv)} invoices.")
                else:
                    st.error(f"Transaction log missing columns: {', '.join(missing_cols_2)}")
            except Exception as e: st.error(f"Error processing transaction file: {e}")

# --- TAB 2: RECONCILIATION (No Changes) ---
with tab_reco:
    # ... code for tab 2 remains the same ...
    st.header("Reconciliation Dashboard")
    if st.session_state.df1_processed is not None and st.session_state.df2_final is not None:
        df1_p = st.session_state.df1_processed
        df2_f = st.session_state.df2_final
        codes_in_contracts = set(df1_p[df1_p['Contract Code'] != '']['Contract Code'].unique())
        codes_in_invoices = set(df2_f[df2_f['Contract Code'] != '']['Contract Code'].unique())
        matched_codes = codes_in_contracts.intersection(codes_in_invoices)
        missing_from_invoices = codes_in_contracts - codes_in_invoices
        unmatched_invoices = codes_in_invoices - codes_in_contracts
        st.subheader("High-Level Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Codes in Contracts", len(codes_in_contracts))
        m2.metric("Codes in Invoices", len(codes_in_invoices))
        m3.metric("✅ Matched Codes", len(matched_codes))
        m4.metric("⚠️ Total Mismatches", len(missing_from_invoices) + len(unmatched_invoices), delta_color="inverse")
        st.divider()
        st.subheader("Discrepancy Details")
        reco_col1, reco_col2 = st.columns(2, gap="large")
        with reco_col1:
            st.warning(f"Contracts Missing from Invoice Log ({len(missing_from_invoices)})")
            if not missing_from_invoices: st.success("All contracts have a matching invoice.")
            else:
                missing_details = df1_p[df1_p['Contract Code'].isin(missing_from_invoices)]
                st.dataframe(missing_details[['Tenants', 'Contract Code', 'Total Value']], use_container_width=True, height=300)
        with reco_col2:
            st.warning(f"Invoices Without a Matching Contract ({len(unmatched_invoices)})")
            if not unmatched_invoices: st.success("All invoices have a matching contract.")
            else:
                unmatched_details = df2_f[df2_f['Contract Code'].isin(unmatched_invoices)]
                st.dataframe(unmatched_details[['Name', 'Contract Code', 'Date', 'Amount']], use_container_width=True, height=300)
    else:
        st.info("⬅️ Please upload and process both files in the 'File Upload' tab to view reconciliation results.")

# --- TAB 3: PAYMENT SCHEDULE (UPDATED WITH SIDE-BY-SIDE VIEW) ---
with tab_schedule:
    st.header("View Contract Schedule & Status")
    
    if st.session_state.df1_processed is not None:
        df1_p = st.session_state.df1_processed
        contract_codes = sorted([code for code in df1_p['Contract Code'].unique() if code])
        selected_code = st.selectbox(
            "Select a Contract Code to analyze:", 
            options=contract_codes,
            index=None, placeholder="Choose a contract..."
        )

        if selected_code:
            contract_details = df1_p[df1_p['Contract Code'] == selected_code].iloc[0]
            schedule_df = generate_payment_schedule(contract_details)

            # Display Main Contract Details
            st.subheader(f"Contract Details: {selected_code}")
            st.text_input("Tenant", contract_details['Tenants'], disabled=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Start Date", contract_details['Start Date'])
            c2.metric("End Date", contract_details['End Date'])
            c3.metric("Installment Amount", f"{contract_details['Installment Amount']:,.2f}")
            
            st.divider()

            # As-Of-Today Analysis
            if st.session_state.df2_final is not None and not schedule_df.empty:
                st.subheader("As-of-Today Status Analysis")
                df2_f = st.session_state.df2_final
                today = pd.to_datetime('today')
                expected_to_date_df = schedule_df[schedule_df['PaymentDate'] <= today]
                estimated_value_as_of_today = expected_to_date_df['Amount'].sum()
                invoices_for_contract = df2_f[df2_f['Contract Code'] == selected_code].copy()
                actual_paid_total = invoices_for_contract['Amount'].sum()
                stat1, stat2, stat3 = st.columns(3)
                stat1.metric("Expected Value (To Date)", f"{estimated_value_as_of_today:,.2f}")
                stat2.metric("Actual Invoiced (Total)", f"{actual_paid_total:,.2f}")
                if not expected_to_date_df.empty:
                    invoices_for_contract['Payment Month'] = pd.to_datetime(invoices_for_contract['Date'], dayfirst=True).dt.strftime('%B %Y')
                    actual_payment_months = set(invoices_for_contract['Payment Month'])
                    missing_invoices_df = expected_to_date_df[~expected_to_date_df['Payment Month'].isin(actual_payment_months)]
                    stat3.metric("⚠️ Missing Invoices (To Date)", len(missing_invoices_df))
                    if not missing_invoices_df.empty:
                        with st.container(border=True):
                            st.error(f"**Missing Invoices for contract `{selected_code}`**")
                            st.dataframe(missing_invoices_df[['Payment Month', 'Amount']], use_container_width=True)
                
            st.divider()

            # --- NEW SIDE-BY-SIDE SCHEDULE COMPARISON ---
            st.subheader("Full Schedule vs. Actual Invoices")
            schedule_col, actual_col = st.columns(2, gap="large")

            with schedule_col:
                st.markdown("##### Expected Payment Schedule")
                if not schedule_df.empty:
                    st.dataframe(schedule_df[['Payment Month', 'Amount']], use_container_width=True, height=400)
                    total_schedule_value = schedule_df['Amount'].sum()
                    st.metric("Total Contract Value", f"{total_schedule_value:,.2f}")
                else:
                    st.error("Could not generate schedule.")
            
            with actual_col:
                st.markdown("##### Actual Invoices from Log")
                if st.session_state.df2_final is not None:
                    df2_f = st.session_state.df2_final
                    invoices_for_contract_display = df2_f[df2_f['Contract Code'] == selected_code]
                    if not invoices_for_contract_display.empty:
                        st.dataframe(invoices_for_contract_display[['Date', 'No.', 'Amount']], use_container_width=True, height=400)
                        total_invoiced_value = invoices_for_contract_display['Amount'].sum()
                        st.metric("Total Invoiced Amount", f"{total_invoiced_value:,.2f}")
                    else:
                        st.info("No invoices found in the log for this contract code.")
                else:
                    st.info("Upload the Transaction Log file to see actual invoices.")

    else:
        st.info("⬅️ Please upload and process the Tenancy Contracts file in the 'File Upload' tab first.")

# --- TAB 4: VIEW FULL DATA (No Changes) ---
with tab_data_view:
    # ... code for tab 4 remains the same ...
    st.header("Explore and Filter Processed Data")
    df1_p = st.session_state.df1_processed
    df2_f = st.session_state.df2_final
    if df1_p is not None or df2_f is not None:
        all_codes = set()
        all_names = set()
        if df1_p is not None:
            all_codes.update(df1_p[df1_p['Contract Code'] != '']['Contract Code'].unique())
            all_names.update(df1_p[df1_p['Tenants'].notna()]['Tenants'].unique())
        if df2_f is not None:
            all_codes.update(df2_f[df2_f['Contract Code'] != '']['Contract Code'].unique())
            all_names.update(df2_f[df2_f['Name'].notna()]['Name'].unique())
        sorted_codes = sorted(list(all_codes))
        sorted_names = sorted(list(all_names))
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            selected_codes = st.multiselect("Filter by Contract Code(s):", options=sorted_codes, placeholder="Select codes...")
        with filter_col2:
            selected_names = st.multiselect("Filter by Tenant/Name:", options=sorted_names, placeholder="Select names...")
        df1_display = df1_p.copy() if df1_p is not None else None
        df2_display = df2_f.copy() if df2_f is not None else None
        if selected_codes:
            if df1_display is not None: df1_display = df1_display[df1_display['Contract Code'].isin(selected_codes)]
            if df2_display is not None: df2_display = df2_display[df2_display['Contract Code'].isin(selected_codes)]
        if selected_names:
            if df1_display is not None: df1_display = df1_display[df1_display['Tenants'].isin(selected_names)]
            if df2_display is not None: df2_display = df2_display[df2_display['Name'].isin(selected_names)]
        st.divider()
    if df1_p is not None:
        with st.expander("View Processed Contract Data", expanded=True):
            st.dataframe(df1_display)
            st.download_button(f"📥 Download Filtered Contract Data ({len(df1_display)} rows)", convert_df_to_csv(df1_display), "filtered_contracts.csv", "text/csv", key='download-contracts-tab4')
    else: st.info("No contract data processed yet.")
    st.divider()
    if df2_f is not None:
        with st.expander("View Processed Invoice Data", expanded=True):
            st.dataframe(df2_display)
            st.download_button(f"📥 Download Filtered Invoice Data ({len(df2_display)} rows)", convert_df_to_csv(df2_display), "filtered_invoices.csv", "text/csv", key='download-invoices-tab4')
    else: st.info("No transaction data processed yet.")
