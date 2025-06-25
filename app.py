# app.py

import streamlit as st
import pandas as pd
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Tenancy Contract Processor",
    page_icon="📄",
    layout="wide"
)

# --- HELPER FUNCTION TO CONVERT DF TO CSV FOR DOWNLOAD ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- APP TITLE AND DESCRIPTION ---
st.title("📄 Tenancy Contract Processor")
st.write(
    "Upload your tenancy contract Excel file to view a cleaned-up table and download the results."
)

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

# --- MAIN LOGIC ---
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')

        # --- DATA PROCESSING ---
        columns_to_keep = [
            'Tenants',
            'Contract Reference',
            'Start Date',
            'End Date',
            'No. of Cheques',
            'Installment Amount',
            'Contractual period (months)',
            'Months Per Cheque',
            'Rent As per Contract',
            'Service as per Contract'
        ]
        
        missing_cols = [col for col in columns_to_keep if col not in df.columns]
        if missing_cols:
            st.error(f"Error: The uploaded file is missing the following required columns: {', '.join(missing_cols)}")
        else:
            df_processed = df[columns_to_keep].copy()

            df_processed['Total Value'] = df_processed['Rent As per Contract'].fillna(0) + df_processed['Service as per Contract'].fillna(0)

            # --- FORMAT DATE COLUMNS (Updated) ---
            date_columns = ['Start Date', 'End Date']
            
            for col in date_columns:
                df_processed[col] = pd.to_datetime(df_processed[col], errors='coerce')
                
                # *** THIS IS THE ONLY LINE THAT CHANGED ***
                df_processed[col] = df_processed[col].dt.strftime('%d-%m-%Y').fillna('')
            # -------------------------------------------

            # --- DISPLAY THE RESULTS ---
            st.header("Processed Contract Data")
            st.write("Here is the reframed table with the 'Total Value' column and formatted dates.")
            
            st.dataframe(df_processed)

            # --- DOWNLOAD BUTTON ---
            csv_data = convert_df_to_csv(df_processed)

            st.download_button(
               label="📥 Download Processed Data as CSV",
               data=csv_data,
               file_name='processed_contracts.csv',
               mime='text/csv',
            )

    except Exception as e:
        st.error(f"An error occurred: {e}")
