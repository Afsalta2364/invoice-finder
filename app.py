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

# --- HELPER FUNCTIONS ---

@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV file for downloading."""
    return df.to_csv(index=False).encode('utf-8')

def extract_code_from_ref(reference):
    """
    Extracts the part of the string after the second '/'.
    Example: 'JA588/AUG24/RIS/125' -> 'RIS/125'
    """
    if not isinstance(reference, str):
        return "" # Return empty string if data is not a string (e.g., NaN)
    
    parts = reference.split('/')
    if len(parts) > 2:
        # Join all parts from the third element (index 2) onwards
        return '/'.join(parts[2:])
    else:
        # Return empty or the original if not in the expected format
        return "" 

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

            # --- Calculation and Formatting ---
            df_processed['Total Value'] = df_processed['Rent As per Contract'].fillna(0) + df_processed['Service as per Contract'].fillna(0)
            
            date_columns = ['Start Date', 'End Date']
            for col in date_columns:
                df_processed[col] = pd.to_datetime(df_processed[col], errors='coerce')
                df_processed[col] = df_processed[col].dt.strftime('%d-%m-%Y').fillna('')

            # --- NEW: EXTRACT CONTRACT CODE ---
            df_processed['Contract Code'] = df_processed['Contract Reference'].apply(extract_code_from_ref)
            # ----------------------------------


            # --- DISPLAY THE RESULTS ---

            # --- NEW: SUMMARY OVERVIEW TABLE ---
            st.header("✨ Summary Overview")
            st.write("A quick overview with the extracted contract codes.")
            
            # Create a smaller DataFrame for the summary view
            summary_df = df_processed[['Tenants', 'Contract Reference', 'Contract Code']]
            st.dataframe(summary_df, use_container_width=True)
            # ----------------------------------


            st.header("Processed Contract Data (Full)")
            st.write("Here is the complete table including the new 'Contract Code' column.")
            
            # Display the full processed DataFrame
            st.dataframe(df_processed)


            # --- DOWNLOAD BUTTON ---
            # The downloadable CSV will now automatically include the new 'Contract Code' column
            csv_data = convert_df_to_csv(df_processed)

            st.download_button(
               label="📥 Download Processed Data as CSV",
               data=csv_data,
               file_name='processed_contracts.csv',
               mime='text/csv',
            )

    except Exception as e:
        st.error(f"An error occurred: {e}")
