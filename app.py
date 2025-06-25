# app.py

import streamlit as st
import pandas as pd
import io
import re  # Import the regular expression module

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Contract & Transaction Reconciliation",
    page_icon="🤝",
    layout="wide"
)

# --- HELPER FUNCTIONS ---

@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV file for downloading."""
    return df.to_csv(index=False).encode('utf-8')

def extract_code_from_ref(reference):
    """
    Finds the last occurrence of the pattern 'CODE/NUMBER' in a string.
    """
    if not isinstance(reference, str):
        return ""

    pattern = r'[A-Z0-9&_-]+/\d+'
    matches = re.findall(pattern, reference)

    if matches:
        return matches[-1]
    else:
        return ""

# --- APP TITLE ---
st.title("🤝 Contract & Transaction Reconciliation Tool")
st.write("Upload the Tenancy Contract file and the Transaction Log file to process and compare them.")

# --- INITIALIZE DATAFRAMES ---
# We initialize these as None so we can check if they've been processed later
df1_processed = None
df2_final = None

# --- UI LAYOUT FOR FILE UPLOADS ---
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
                # Assign the processed dataframe to our variable
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

# --- COLUMN 2: TRANSACTION LOG ---
with col2:
    st.header("2. Process Transaction Log")
    uploaded_file_2 = st.file_uploader("Upload Transaction Log Excel File", type="xlsx", key="transactions")

    if uploaded_file_2 is not None:
        try:
            df2 = pd.read_excel(uploaded_file_2, engine='openpyxl')
            
            cols_2 = ['Date', 'Transaction Type', 'No.', 'Name', 'Amount']
            
            missing_cols_2 = [col for col in cols_2 if col not in df2.columns]
            if not missing_cols_2:
                df2_invoices = df2[df2['Transaction Type'].str.lower() == 'invoice'].copy()
                initial_invoice_count = len(df2_invoices)
                
                df2_invoices['Contract Code'] = df2_invoices['No.'].apply(extract_code_from_ref)
                df2_invoices['Date'] = pd.to_datetime(df2_invoices['Date'], errors='coerce').dt.strftime('%d-%m-%Y').fillna('')
                # Assign the final processed dataframe to our variable
                df2_final = df2_invoices[['Date', 'Name', 'No.', 'Contract Code', 'Amount']]

                st.subheader("Count Check")
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric("Total Invoices in File", initial_invoice_count)
                extracted_code_count = (df2_final['Contract Code'] != '').sum()
                metric_col2.metric("Total Codes Extracted", extracted_code_count)

                st.subheader("⚠️ Invoices with Extraction Issues")
                missing_codes_df = df2_final[df2_final['Contract Code'] == '']
                with st.expander(f"Found {len(missing_codes_df)} invoices with issues. Click to see details."):
                    if not missing_codes_df.empty:
                        st.dataframe(missing_codes_df[['Date', 'Name', 'No.', 'Amount']])
                    else:
                        st.success("✅ All invoices have a valid, extractable contract code.")

                st.subheader("Processed Invoice Data")
                st.dataframe(df2_final)
                
                csv_data_2 = convert_df_to_csv(df2_final)
                st.download_button("📥 Download Invoice Data (CSV)", csv_data_2, "processed_invoices.csv", "text/csv", key='download-invoices')
            else:
                st.error(f"Transaction log missing columns: **{', '.join(missing_cols_2)}**")
                st.write("Columns found in your file:", df2.columns.tolist())

        except Exception as e:
            st.error(f"An error occurred processing the transaction file: {e}")


# --- NEW SECTION: RECONCILIATION ---
# This block will only run if both DataFrames have been successfully created.
st.divider() # Adds a horizontal line for visual separation

if df1_processed is not None and df2_final is not None:
    st.header("📊 Reconciliation Results")
    
    # Get unique, non-empty contract codes from both dataframes
    codes_in_contracts = set(df1_processed[df1_processed['Contract Code'] != '']['Contract Code'].unique())
    codes_in_invoices = set(df2_final[df2_final['Contract Code'] != '']['Contract Code'].unique())
    
    # Find the differences using set operations
    matched_codes = codes_in_contracts.intersection(codes_in_invoices)
    missing_from_invoices = codes_in_contracts - codes_in_invoices
    unmatched_invoices = codes_in_invoices - codes_in_contracts
    
    # --- Display Summary Metrics ---
    st.subheader("Summary Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Codes in Contracts", len(codes_in_contracts))
    m2.metric("Codes in Invoices", len(codes_in_invoices))
    m3.metric("Matched Codes", len(matched_codes))
    m4.metric("Total Mismatches", len(missing_from_invoices) + len(unmatched_invoices))
    
    st.divider()
    
    # --- Display Detailed Mismatch Lists ---
    reco_col1, reco_col2 = st.columns(2)
    
    with reco_col1:
        st.subheader(f"⚠️ Contracts Missing from Invoice Log ({len(missing_from_invoices)})")
        if not missing_from_invoices:
            st.success("✅ All contracts have a matching invoice.")
        else:
            # Show the contract details for the missing items
            missing_details = df1_processed[df1_processed['Contract Code'].isin(missing_from_invoices)]
            st.dataframe(missing_details[['Tenants', 'Contract Code', 'Total Value']], use_container_width=True)

    with reco_col2:
        st.subheader(f"⚠️ Invoices Without a Matching Contract ({len(unmatched_invoices)})")
        if not unmatched_invoices:
            st.success("✅ All invoices have a matching contract.")
        else:
            # Show the invoice details for the unmatched items
            unmatched_details = df2_final[df2_final['Contract Code'].isin(unmatched_invoices)]
            st.dataframe(unmatched_details[['Name', 'Contract Code', 'Date', 'Amount']], use_container_width=True)
