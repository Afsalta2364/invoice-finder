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

# --- NEW HELPER FUNCTION FOR PAYMENT SCHEDULE ---
def generate_payment_schedule(contract_row):
    """Generates a month-by-month payment schedule from a contract's details."""
    try:
        # Convert string dates to datetime objects, handling the 'DD-MM-YYYY' format
        start_date = pd.to_datetime(contract_row['Start Date'], dayfirst=True)
        end_date = pd.to_datetime(contract_row['End Date'], dayfirst=True)
        installment_amount = contract_row['Installment Amount']

        # Generate a date for the start of each month within the contract period
        monthly_dates = pd.date_range(start=start_date, end=end_date, freq='MS')

        if monthly_dates.empty:
            return pd.DataFrame() # Return empty if no full months

        # Create the schedule DataFrame
        schedule_df = pd.DataFrame({
            'Payment Month': monthly_dates.strftime('%B %Y'), # Format as 'Month Year'
            'Amount': installment_amount
        })
        return schedule_df
    except (ValueError, TypeError):
        # Handle cases where dates are invalid or missing
        return pd.DataFrame()


# --- SESSION STATE INITIALIZATION ---
if 'df1_processed' not in st.session_state:
    st.session_state.df1_processed = None
if 'df2_final' not in st.session_state:
    st.session_state.df2_final = None

# --- APP TITLE ---
st.title("📊 Advanced Contract & Transaction Reconciliation Dashboard")
st.markdown("A tool to process, compare, and analyze tenancy contracts and transactions.")

# --- CREATE TABS FOR A CLEANER WORKFLOW ---
tab_upload, tab_reco, tab_schedule, tab_data_view = st.tabs([
    "📂 **Step 1: File Upload**",
    "📈 **Step 2: Reconciliation**",
    "📅 **Step 3: Payment Schedule**",
    "📄 **View Full Data**"
])


# --- TAB 1: FILE UPLOAD AND PROCESSING ---
with tab_upload:
    st.header("Upload Your Files Here")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("Tenancy Contracts File")
        uploaded_file_1 = st.file_uploader("Upload the main contract file.", type="xlsx", key="contracts")
        if uploaded_file_1:
            # Processing logic for file 1...
            try:
                df1 = pd.read_excel(uploaded_file_1, engine='openpyxl')
                cols_1 = ['Tenants', 'Contract Reference', 'Start Date', 'End Date', 'No. of Cheques', 
                          'Installment Amount', 'Contractual period (months)', 'Months Per Cheque', 
                          'Rent As per Contract', 'Service as per Contract']
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
            except Exception as e:
                st.error(f"Error processing contract file: {e}")

    with col2:
        st.subheader("Transaction Log File")
        uploaded_file_2 = st.file_uploader("Upload the invoice transaction log.", type="xlsx", key="transactions")
        if uploaded_file_2:
            # Processing logic for file 2...
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
            except Exception as e:
                st.error(f"Error processing transaction file: {e}")

# --- TAB 2: RECONCILIATION RESULTS ---
with tab_reco:
    st.header("Reconciliation Dashboard")
    # Reconciliation logic...
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
            if not missing_from_invoices:
                st.success("All contracts have a matching invoice.")
            else:
                missing_details = df1_p[df1_p['Contract Code'].isin(missing_from_invoices)]
                st.dataframe(missing_details[['Tenants', 'Contract Code', 'Total Value']], use_container_width=True, height=300)
        with reco_col2:
            st.warning(f"Invoices Without a Matching Contract ({len(unmatched_invoices)})")
            if not unmatched_invoices:
                st.success("All invoices have a matching contract.")
            else:
                unmatched_details = df2_f[df2_f['Contract Code'].isin(unmatched_invoices)]
                st.dataframe(unmatched_details[['Name', 'Contract Code', 'Date', 'Amount']], use_container_width=True, height=300)
    else:
        st.info("⬅️ Please upload and process both files in the 'File Upload' tab to view reconciliation results.")

# --- TAB 3: PAYMENT SCHEDULE ---
with tab_schedule:
    st.header("View Monthly Payment Schedule")
    
    if st.session_state.df1_processed is not None:
        df1_p = st.session_state.df1_processed
        
        # Create a dropdown with sorted, unique contract codes
        contract_codes = sorted([code for code in df1_p['Contract Code'].unique() if code])
        selected_code = st.selectbox(
            "Select a Contract Code to view its schedule:", 
            options=contract_codes,
            index=None, # Makes the default selection empty
            placeholder="Choose a contract..."
        )

        if selected_code:
            # Get the full details for the selected contract
            contract_details = df1_p[df1_p['Contract Code'] == selected_code].iloc[0]

            st.subheader(f"Details for Contract: {selected_code}")
            
            # Display key contract details in a clean layout
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Start Date", contract_details['Start Date'])
                st.metric("Rent As per Contract", f"{contract_details['Rent As per Contract']:,.2f}")
            with c2:
                st.metric("End Date", contract_details['End Date'])
                st.metric("Service as per Contract", f"{contract_details['Service as per Contract']:,.2f}")
            with c3:
                st.metric("Installment Amount", f"{contract_details['Installment Amount']:,.2f}")
                st.metric("Total Contract Value", f"{contract_details['Total Value']:,.2f}")

            st.text_input("Full Contract Reference", contract_details['Contract Reference'], disabled=True)
            st.divider()

            # Generate and display the monthly schedule
            st.subheader("Generated Payment Schedule")
            schedule_df = generate_payment_schedule(contract_details)

            if not schedule_df.empty:
                st.dataframe(schedule_df, use_container_width=True)
                # Verify the total
                total_schedule_value = schedule_df['Amount'].sum()
                st.success(f"**Total Schedule Value:** `{total_schedule_value:,.2f}`")
            else:
                st.error("Could not generate a payment schedule. Please check the contract's Start and End dates.")

    else:
        st.info("⬅️ Please upload and process the Tenancy Contracts file in the 'File Upload' tab first.")

# --- TAB 4: VIEW FULL DATA ---
with tab_data_view:
    st.header("Explore Processed Data")
    # View full data logic...
    if st.session_state.df1_processed is not None:
        with st.expander("View Full Processed Contract Data", expanded=True):
            st.dataframe(st.session_state.df1_processed)
            st.download_button("📥 Download Contract Data (CSV)", convert_df_to_csv(st.session_state.df1_processed), "processed_contracts.csv", "text/csv", key='download-contracts-tab4')
    else:
        st.info("No contract data processed yet.")
    st.divider()
    if st.session_state.df2_final is not None:
        with st.expander("View Full Processed Invoice Data", expanded=True):
            st.dataframe(st.session_state.df2_final)
            st.download_button("📥 Download Invoice Data (CSV)", convert_df_to_csv(st.session_state.df2_final), "processed_invoices.csv", "text/csv", key='download-invoices-tab4')
    else:
        st.info("No transaction data processed yet.")
