import pandas as pd
import pyodbc
import uuid

# Define file path and database connection details
file_path = 'data/IndeedJobListing_.xlsx'
server = 'LAPTOP-FOASEDN5\\SQLEXPRESS'
database = 'WebScrapedData'

# Read the Excel file into a DataFrame
df = pd.read_excel(file_path)

# Clean and preprocess data
# For NVARCHAR columns, you may not need specific cleaning unless you have format issues
# Ensure that any problematic data is handled or cleaned
def clean_text(value):
    if pd.isna(value):
        return None  # Or '' if you prefer empty strings
    return str(value).strip()  # Remove leading/trailing whitespace

# Apply cleaning function to relevant columns
df['Salary Range'] = df['Salary Range'].apply(clean_text)
df['Job Title'] = df['Job Title'].apply(clean_text)
df['Description'] = df['Description'].apply(clean_text)
df['Contract Type'] = df['Contract Type'].apply(clean_text)
df['Company'] = df['Company'].apply(clean_text)
df['City'] = df['City'].apply(clean_text)
df['URL'] = df['URL'].apply(clean_text)

# Establish a connection to SQL Server using Windows Authentication
conn_str = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={server};'
    f'DATABASE={database};'
    f'Trusted_Connection=yes;'
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Iterate through the DataFrame and insert rows into the IndeedModels table
for index, row in df.iterrows():
    # Generate a UUID for each record
    unique_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO IndeedModels (Id, JobTitle, Description, ContractType, Company, City, SalaryRange, URL)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, unique_id, row['Job Title'], row['Description'], row['Contract Type'], row['Company'], row['City'], row['Salary Range'], row['URL'])

# Commit the transaction
conn.commit()

# Close the connection
cursor.close()
conn.close()

print("Data imported successfully.")
