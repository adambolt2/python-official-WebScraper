import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse, parse_qs, quote_plus

# Function to extract the value of the 'vjk' parameter from the URL
def extract_vjk_from_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get('vjk', [None])[0]

# Function to extract salary from the job description using regex patterns
def extract_salary_from_description(description):
    salary_pattern = re.compile(r'\b(\£\d{1,3}(,\d{3})*)\s*-\s*(\£\d{1,3}(,\d{3})*)\b', re.IGNORECASE)
    match = salary_pattern.search(description)
    
    if match:
        return f"{match.group(1)} - {match.group(3)}"
    return None

# Function to construct the URL manually to avoid unwanted encoding issues
def construct_url(base_url, params):
    query_string = '&'.join(f"{quote_plus(k)}={quote_plus(v)}" for k, v in params.items())
    return f"{base_url}?{query_string}"

# Function to post job data to the API
def post_job_data(job_data):
    try:
        response = requests.post("https://localhost:7270/api/IndeedModels/fdtjgz8r", json=job_data, verify=False)
        if response.status_code == 201:
            print(f"Job successfully added: {job_data['Job Title']}")
        else:
            print(f"Failed to add job: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        print(f"An error occurred while posting job data: {e}")

# Function to process a single page of job listings
def process_page(driver, page_number, dff):
    url = f"https://uk.indeed.com/jobs?q=software+developer&l=United+Kingdom&start={page_number}"
    driver.get(url)
    time.sleep(60)  # Wait for the page to load

    soup = BeautifulSoup(driver.page_source, 'html5lib')
    results = soup.find(id='mosaic-jobResults')
    job_elems = results.find_all('div', class_='job_seen_beacon')

    for index, job_elem in enumerate(job_elems):
        try:
            # Find the parent anchor tag that contains the job title
            A = job_elem.find('a', class_='jcs-JobTitle')
            Title = A.text if A else "Title not found"
            print(f"Found title: {Title}")
            
            if not Title:
                print("No title found. Skipping this job.")
                continue
            
            try:
                company_info_container = job_elem.find('span', attrs={'data-testid': 'company-name'})
                Company = company_info_container.text if company_info_container else "Company not found"
                print(f"Company found: {Company}")
            except Exception as e:
                Company = "Company not found"
                print(f"Company extraction failed: {e}")

            # Click on the anchor tag to load the job details page
            selenium_job_elem = driver.find_elements(By.CLASS_NAME, 'job_seen_beacon')[index]
            selenium_title_elem = selenium_job_elem.find_element(By.CSS_SELECTOR, 'a.jcs-JobTitle')
            driver.execute_script("arguments[0].scrollIntoView(true);", selenium_title_elem)
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.jcs-JobTitle')))
            selenium_title_elem.click()
            time.sleep(2)  # Wait for the description to load

            # Find the job description using Selenium
            try:
                job_component = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'jobsearch-JobComponent')))
                D = job_component.find_element(By.ID, 'jobDescriptionText')
                Description = D.text if D else "Description not found"
            except Exception as e:
                Description = "Description not found"

            # Extract salary and experience
            try:
                salary_and_job_type = job_component.find_element(By.ID, 'salaryInfoAndJobType')
                spans = salary_and_job_type.find_elements(By.TAG_NAME, 'span')
                salary = None
                experience = None

                for span in spans:
                    text = span.text.lower()
                    if any(keyword in text for keyword in ['permanent', 'full-time', 'contract', 'temporary', 'apprenticeship', 'part-time']):
                        experience = text.replace('-', ' ')
                    else:
                        salary = text

                # Default to "Not-Mentioned" if no salary or experience is found
                Salary = salary if salary else "Not-Mentioned"
                Exp = experience if experience else "Not-Mentioned"

            except Exception as e:
                Salary = "Not-Mentioned"
                Exp = "Contract Type not found"

            # If salary is still not found, try to extract from the description
            if Salary == "Not-Mentioned":
                extracted_salary = extract_salary_from_description(Description)
                if extracted_salary:
                    Salary = extracted_salary

            # Extract location
            try:
                location_elem = job_component.find_element(By.CSS_SELECTOR, 'div[data-testid="inlineHeader-companyLocation"] div')
                City = location_elem.text if location_elem else "Location not found"
            except Exception as e:
                City = "Location not found"

            # Date Posted
            D = job_elem.find('span', class_='job-post-day')
            Date = D.text if D else "Date not found"
            current_url = driver.current_url
            vjk = extract_vjk_from_url(current_url)
            
            # Construct the final URL
            if vjk:
                base_url = 'https://uk.indeed.com/jobs'
                query_params = {
                    'q': 'software developer',
                    'l': 'United Kingdom',
                    'from': 'searchOnHP',
                    'vjk': vjk
                }
                final_url = construct_url(base_url, query_params)
                URL = final_url
                print(f"Constructed URL: {final_url}")
            else:
                URL = driver.current_url
                print("vjk parameter not found in the URL.")
                
            
            if not City or not Company or not Description:
                print("Incomplete job information. Skipping this job.")
                continue
              
            # Check for duplicates before posting
            if not ((dff['City'] == City) & (dff['Company'] == Company) & (dff['Description'] == Description)).any():
                job_data = {
                    "JobTitle": Title,
                    "Description": Description,
                    "ContractType": Exp,
                    "Company": Company,
                    "City": City,
                    "SalaryRange": Salary,
                    "URL": URL
                }
                post_job_data(job_data)
                # Add job to the DataFrame
                dff = pd.concat([dff, pd.DataFrame([job_data])], ignore_index=True)
            else:
                print(f"Duplicate job entry found: {Title} - Skipping")

        except Exception as e:
            print(f"An error occurred while processing job details: {e}")

    return len(job_elems) > 0, dff

def main():
    page_number = 0
    dff = pd.DataFrame(columns=['Job Title', 'Description', 'Contract Type', 'Company', 'City', 'Salary Range', 'URL'])
    
    while True:
        try:
            chrome_options = uc.ChromeOptions()
            chrome_options.add_argument("--incognito")
            driver = uc.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            has_jobs, dff = process_page(driver, page_number, dff)
            driver.close()

            # Check if there are no more job listings
            if not has_jobs:
                print("No more jobs found. Exiting.")
                break

            # Increment the page number for the next iteration
            page_number += 10
        except Exception as e:
            print(f"An error occurred: {e}")
            page_number += 10  # Increment page number and try again

if __name__ == "__main__":
    main()
