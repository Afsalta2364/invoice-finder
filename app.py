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

# --- HELPER FUNCTIONS (No changes needed here) ---

@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV file for downloading."""
    return df.to_csv(index=False).encode('utf-8')

def extract_code_from_ref(reference):
    """Finds the last occurrence of the pattern 'CODE/NUMBER' in a string."""
    if not isinstance(reference, str):
        return ""
    pattern = r'[A-Z0-9&_-]+/\d+'
    matches = re.findall(pattern, reference)
    if matches:
        return matches[-1]
    else:
        return ""

# --- SESSION STATE INITIALIZATION ---
# This is crucial for passing data between tabs.
if 'df1_processed' not in st.session_state:
    st.session_state.df1_processed = None
if 'df2_final' not in st.session_state:
    st.session_state.df2_final = None

# --- APP TITLE ---
st.title("📊 Advanced Contract & Transaction Reconciliation Dashboard")
st.markdown("A tool to simplify contract reconciliation by processing, comparing, and highlighting discrepancies between files.")

# --- CREATE TABS FOR A CLEANER WORKFLOW ---
tab_upload, tab_reco, tab_data_view = st.tabs([
    "📂 **Step 1: File Upload & Processing**", 
    "📈 **Step 2: Reconciliation Results**",
    "📄 **View Full Processed Data**"
])


# --- TAB 1: FILE UPLOAD AND PROCESSING ---
with tab_upload:
    st.header("Upload Your Files Here")
    col1, col2 = st.columns(2, gap="large")

    # --- UPLOAD AND PROCESS CONTRACT FILE ---
    with col1:
        st.subheader("Tenancy Contracts File")
        uploaded_file_1 = st.file_uploader("Upload the main contract file.", type="xlsx", key="contracts")
        
        if uploaded_file_1:
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
                    
                    # Store in session state
                    st.session_state.df1_processed = df1_p
                    st.success(f"✅ Contract file processed successfully! Found {len(df1_p)} records.")
                else:
                    st.error(f"Contract file missing columns: {', '.join(missing_cols_1)}")
            except Exception as e:
                st.error(f"Error processing contract file: {e}")

    # --- UPLOAD AND PROCESS TRANSACTION LOG ---
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
                    
                    # Store in session state
                    st.session_state.df2_final = df2_inv[['Date', 'Name', 'No.', 'Contract Code', 'Amount']]
                    st.success(f"✅ Transaction log processed successfully! Found {len(df2_inv)} invoices.")
                else:
                    st.error(f"Transaction log missing columns: {', '.join(missing_cols_2)}")
            except Exception as e:
                st.error(f"Error processing transaction file: {e}")

# --- TAB 2: RECONCILIATION RESULTS ---
with tab_reco:
    st.header("Reconciliation Dashboard")
    
    # Check if both files have been processed before showing results
    if st.session_state.df1_processed is not None and st.session_state.df2_final is not None:
        df1_p = st.session_state.df1_processed
        df2_f = st.session_state.df2_final

        # Perform reconciliation logic
        codes_in_contracts = set(df1_p[df1_p['Contract Code'] != '']['Contract Code'].unique())
        codes_in_invoices = set(df2_f[df2_f['Contract Code'] != '']['Contract Code'].unique())
        
        matched_codes = codes_in_contracts.intersection(codes_in_invoices)
        missing_from_invoices = codes_in_contracts - codes_in_invoices
        unmatched_invoices = codes_in_invoices - codes_in_contracts
        
        # Display Summary Metrics
        st.subheader("High-Level Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Codes in Contracts", len(codes_in_contracts))
        m2.metric("Codes in Invoices", len(codes_in_invoices))
        m3.metric("✅ Matched Codes", len(matched_codes), help="Codes found in both files.")
        m4.metric("⚠️ Total Mismatches", len(missing_from_invoices) + len(unmatched_invoices), delta_color="inverse")
        
        st.divider()

        # Display Detailed Mismatch Lists
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
        st.info("⬅️ Please upload and process both files in the 'File Upload & Processing' tab to view the reconciliation results.")
        st.image("https://i.imgur.com/v2dKj3y.png", width=300) # A visual cue

# --- TAB 3: VIEW FULL DATA ---
with tab_data_view:
    st.header("Explore Processed Data")
    
    if st.session_state.df1_processed is not None:
        with st.expander("View Full Processed Contract Data", expanded=True):
            st.dataframe(st.session_state.df1_processed)
            st.download_button(
                "📥 Download Contract Data (CSV)", 
                convert_df_to_csv(st.session_state.df1_processed), 
                "processed_contracts.csv", "text/csv", key='download-contracts-tab3'
            )
    else:
        st.info("No contract data processed yet.")

    st.divider()

    if st.session_state.df2_final is not None:
        with st.expander("View Full Processed Invoice Data & Extraction Issues", expanded=True):
            df2_full = st.session_state.df2_final
            st.dataframe(df2_full)
            st.download_button(
                "📥 Download Invoice Data (CSV)", 
                convert_df_to_csv(df2_full), 
                "processed_invoices.csv", "text/csv", key='download-invoices-tab3'
            )

            # Show extraction issues here as well for easy debugging
            missing_codes_df = df2_full[df2_full['Contract Code'] == '']
            if not missing_codes_df.empty:
                st.warning("Invoices with Extraction Issues")
                st.dataframe(missing_codes_df[['Date', 'Name', 'No.', 'Amount']])
    else:
        st.info("No transaction data processed yet.")
