# app.py

import streamlit as st
import pandas as pd
import io

# --- PAGE CONFIGURATION ---
# Use st.set_page_config() as the first Streamlit command in your script.
st.set_page_config(
    page_title="Tenancy Contract Processor",
    page_icon="📄",
    layout="wide"  # "wide" layout uses the entire screen width.
)

# --- HELPER FUNCTION TO CONVERT DF TO CSV FOR DOWNLOAD ---
# This function is important for the download button to work correctly.
@st.cache_data
def convert_df_to_csv(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

# --- APP TITLE AND DESCRIPTION ---
st.title("📄 Tenancy Contract Processor")
st.write(
    "Upload your tenancy contract Excel file to view a cleaned-up table and download the results."
)

# --- FILE UPLOADER ---
# The widget to upload files. We restrict it to Excel files.
uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

# --- MAIN LOGIC ---
# This block of code will only run if the user has uploaded a file.
if uploaded_file is not None:
    try:
        # Read the uploaded Excel file into a pandas DataFrame.
        # 'engine='openpyxl'' is required for .xlsx files.
        df = pd.read_excel(uploaded_file, engine='openpyxl')

        # --- DATA PROCESSING ---
        
        # 1. Define the list of columns we want to keep.
        #    This makes the code clean and easy to update.
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
        
        # Check if all required columns exist in the uploaded file
        missing_cols = [col for col in columns_to_keep if col not in df.columns]
        if missing_cols:
            st.error(f"Error: The uploaded file is missing the following required columns: {', '.join(missing_cols)}")
        else:
            # 2. Create a new DataFrame with only the desired columns.
            #    Using .copy() prevents a pandas SettingWithCopyWarning.
            df_processed = df[columns_to_keep].copy()

            # 3. Create the 'Total Value' column by adding the two specified columns.
            #    We use .fillna(0) to handle any potential empty cells gracefully.
            df_processed['Total Value'] = df_processed['Rent As per Contract'].fillna(0) + df_processed['Service as per Contract'].fillna(0)

            # --- DISPLAY THE RESULTS ---

            st.header("Processed Contract Data")
            st.write("Here is the reframed table with the 'Total Value' column.")
            
            # Display the processed DataFrame. st.dataframe is interactive (sortable, etc.).
            st.dataframe(df_processed)

            # --- DOWNLOAD BUTTON ---
            
            # Convert the processed DataFrame to a CSV format in memory.
            csv_data = convert_df_to_csv(df_processed)

            st.download_button(
               label="📥 Download Processed Data as CSV",
               data=csv_data,
               file_name='processed_contracts.csv',
               mime='text/csv',
            )

    except Exception as e:
        # If any error occurs during file reading or processing, show an error message.
        st.error(f"An error occurred: {e}")
