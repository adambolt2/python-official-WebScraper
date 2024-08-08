import os
import pandas as pd
import pyodbc
import uuid

# Define folder path and database connection details
folder_path = 'data'
server = 'LAPTOP-FOASEDN5\\SQLEXPRESS'
database = 'WebScrapedData'

# Function to clean and preprocess data
def clean_text(value):
    if pd.isna(value):
        return None  # Or '' if you prefer empty strings
    return str(value).strip()  # Remove leading/trailing whitespace

# Function to process a single file
def process_file(file_path):
    print(f"Processing file: {file_path}")
    
    try:
        # Read the Excel file into a DataFrame
        df = pd.read_excel(file_path, engine='openpyxl')  # Specify engine if needed
        
        # Print column names for debugging
        print(f"Columns in file: {df.columns.tolist()}")
        
        # Clean and preprocess data
        df.columns = df.columns.str.strip()  # Strip any extra spaces from column names
        required_columns = ['Job Title', 'Description', 'Company', 'City', 'Salary Range', 'URL']
        
        # Check if all required columns are present
        for col in required_columns:
            if col not in df.columns:
                print(f"Warning: Column '{col}' is missing in file {file_path}")
                continue
        
        # Apply cleaning function to relevant columns if they exist
        for col in required_columns:
            if col in df.columns:
                df[col] = df[col].apply(clean_text)
        
        # Establish a connection to SQL Server using Windows Authentication
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'Trusted_Connection=yes;'
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Iterate through the DataFrame and insert rows into the TotalJobsModels table
        for index, row in df.iterrows():
            # Generate a UUID for each record
            unique_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO TotalJobsModels (Id, JobTitle, Description, Company, City, SalaryRange, URL)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, unique_id, row.get('Job Title'), row.get('Description'), row.get('Company'), row.get('City'), row.get('Salary Range'), row.get('URL'))
        
        # Commit the transaction
        conn.commit()
        
        # Close the connection
        cursor.close()
        conn.close()
        
        print("Data imported successfully.")
    
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

# Iterate through all .xlsx files in the folder
for file in os.listdir(folder_path):
    if file.endswith(".xlsx") and not file.startswith("~"):
        file_path = os.path.join(folder_path, file)
        process_file(file_path)
