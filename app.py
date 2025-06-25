# app.py

import streamlit as st
import pandas as pd
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Contract & Transaction Processor",
    page_icon="🤝",
    layout="wide"
)

# --- HELPER FUNCTIONS ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def extract_code_from_ref(reference):
    if not isinstance(reference, str): return ""
    parts = reference.split('/')
    if len(parts) > 2: return '/'.join(parts[2:])
    else: return ""

# --- APP TITLE ---
st.title("🤝 Contract & Transaction Reconciliation Tool")
st.write("Upload the Tenancy Contract file and the Transaction Log file to process and prepare them for reconciliation.")

# --- UI LAYOUT ---
col1, col2 = st.columns(2)

# --- COLUMN 1: TENANCY CONTRACTS ---
with col1:
    st.header("1. Process Tenancy Contracts")
    uploaded_file_1 = st.file_uploader("Upload Contract Excel File", type="xlsx", key="contracts")

    if uploaded_file_1 is not None:
        try:
            df1 = pd.read_excel(uploaded_file_1, engine='openpyxl')
            
            cols_1 = ['Tenants', 'Contract Reference', 'Start Date', 'End Date', 'No. of Cheques', 
                      'Installment Amount', 'Contractual period (months)', 'Months Per Cheque', 
                      'Rent As per Contract', 'Service as per Contract']
            
            missing_cols_1 = [col for col in cols_1 if col not in df1.columns]
            if not missing_cols_1:
                df1_processed = df1[cols_1].copy()
                df1_processed['Total Value'] = df1_processed['Rent As per Contract'].fillna(0) + df1_processed['Service as per Contract'].fillna(0)
                for col in ['Start Date', 'End Date']:
                    df1_processed[col] = pd.to_datetime(df1_processed[col], errors='coerce').dt.strftime('%d-%m-%Y').fillna('')
                df1_processed['Contract Code'] = df1_processed['Contract Reference'].apply(extract_code_from_ref)

                st.subheader("Summary Overview")
                st.dataframe(df1_processed[['Tenants', 'Contract Reference', 'Contract Code']], use_container_width=True)
                st.subheader("Full Processed Contract Data")
                st.dataframe(df1_processed)

                csv_data_1 = convert_df_to_csv(df1_processed)
                st.download_button("📥 Download Contract Data (CSV)", csv_data_1, "processed_contracts.csv", "text/csv", key='download-contracts')
            else:
                st.error(f"Contract file missing columns: **{', '.join(missing_cols_1)}**")
                st.info("Columns found in file:", df1.columns.tolist())
        
        except Exception as e:
            st.error(f"An error occurred processing the contract file: {e}")

# --- COLUMN 2: TRANSACTION LOG (UPDATED) ---
with col2:
    st.header("2. Process Transaction Log")
    uploaded_file_2 = st.file_uploader("Upload Transaction Log Excel File", type="xlsx", key="transactions")

    if uploaded_file_2 is not None:
        try:
            df2 = pd.read_excel(uploaded_file_2, engine='openpyxl')
            
            # *** CHANGE 1: Update the list of expected column names ***
            cols_2 = ['Date', 'Transaction Type', 'No.', 'Name', 'Amount']
            
            missing_cols_2 = [col for col in cols_2 if col not in df2.columns]
            if not missing_cols_2:
                # *** CHANGE 2: Use "Transaction Type" for filtering ***
                df2_invoices = df2[df2['Transaction Type'].str.lower() == 'invoice'].copy()
                initial_invoice_count = len(df2_invoices)
                
                # *** CHANGE 3: Use "No." for extracting the contract code ***
                df2_invoices['Contract Code'] = df2_invoices['No.'].apply(extract_code_from_ref)
                
                df2_invoices['Date'] = pd.to_datetime(df2_invoices['Date'], errors='coerce').dt.strftime('%d-%m-%Y').fillna('')
                
                # *** CHANGE 4: Use "No." in the final displayed table ***
                df2_final = df2_invoices[['Date', 'Name', 'No.', 'Contract Code', 'Amount']]

                st.subheader("Count Check")
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric("Total Invoices in File", initial_invoice_count)
                metric_col2.metric("Unique Contract Codes", df2_final['Contract Code'].nunique())

                st.subheader("Processed Invoice Data")
                st.dataframe(df2_final)
                
                csv_data_2 = convert_df_to_csv(df2_final)
                st.download_button("📥 Download Invoice Data (CSV)", csv_data_2, "processed_invoices.csv", "text/csv", key='download-invoices')
            else:
                st.error(f"Transaction log missing columns: **{', '.join(missing_cols_2)}**")
                st.info("Please check for typos, extra spaces, or case sensitivity in your Excel file's headers.")
                st.write("Columns found in your file:", df2.columns.tolist())

        except Exception as e:
            st.error(f"An error occurred processing the transaction file: {e}")
