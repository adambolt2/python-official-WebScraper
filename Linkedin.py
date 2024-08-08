import datetime
import os
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
import requests
import pandas as pd

# Function to extract employment type and seniority level from job criteria
def extract_job_criteria(job_criteria_list):
    employment_type = "Not Mentioned"
    seniority_level = "Not Mentioned"

    criteria_items = job_criteria_list.find_all('li', class_='description__job-criteria-item')
    for item in criteria_items:
        header = item.find('h3', class_='description__job-criteria-subheader').text.strip()
        text = item.find('span', class_='description__job-criteria-text').text.strip()
        if header == "Employment type":
            employment_type = text
        elif header == "Seniority level":
            seniority_level = text

    return employment_type, seniority_level

# Function to check for duplicates in the DataFrame
def is_duplicate(dff, Title, Company, Date, URL):
    duplicate = dff[(dff['Job Title'] == Title) & 
                    (dff['Date Posted'] == Date) & 
                    (dff['Company'] == Company) &
                    (dff['URL'] == URL)]
    return not duplicate.empty

# Function to process a single page of job listings
def process_page(driver, dff):
    url = "https://www.linkedin.com/jobs/search?keywords=Software%20Engineer&location=United%20Kingdom&geoId=101165590&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0"
    driver.get(url)
    time.sleep(3)  # Wait for the page to load

    attempts = 0
    max_attempts = 30

    while True:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        results = soup.find('ul', class_='jobs-search__results-list')

        if not results:
            print("No job listings found on this page.")
            return dff

        job_elems = results.find_all('li')

        new_jobs_found = False
        initial_job_count = len(job_elems)  # Track the initial number of jobs on the page

        for index in range(len(job_elems)):
            job_elem = job_elems[index]

            try:
                # Extract job title
                A = job_elem.find('a', class_='base-card__full-link')
                Title = A.find('span', class_='sr-only').text.strip() if A else "Title not found"

                # Extract company name
                company_link = job_elem.find('a', class_='hidden-nested-link')
                Company = company_link.text.strip() if company_link else "Company not found"

                # Extract job posting date
                D = job_elem.find('time', class_='job-search-card__listdate')
                Date = D['datetime'] if D else "Date not found"

                # Get job URL
                URL = A['href'] if A else "URL not found"

                # Check for duplicates
                if is_duplicate(dff, Title, Company, Date, URL):
                    print("Duplicate job found. Skipping...")
                    continue

                # Click on the job to load the job details page
                selenium_job_elem = driver.find_elements(By.CSS_SELECTOR, 'ul.jobs-search__results-list li')[index]
                selenium_job_elem.click()
                time.sleep(2)  # Wait for the description to load

                # Extract job description from the expanded content
                try:
                    job_details = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.show-more-less-html__markup.relative.overflow-hidden'))
                    )
                    Description = job_details.text if job_details else ""
                except Exception as e:
                    Description = ""

                # Skip this job if no description is found
                if not Description:
                    continue

                # Extract job criteria (employment type, seniority level, etc.)
                Employment_type = "Not Mentioned"
                Seniority_level = "Not Mentioned"
                try:
                    job_details_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    results2 = job_details_soup.find('ul', class_='description__job-criteria-list')
                    if results2:
                        Employment_type, Seniority_level = extract_job_criteria(results2)
                except Exception as e:
                    print(f"Job criteria not found or error: {e}")

                # Extract location
                location_elem = job_elem.find('span', class_='job-search-card__location')
                City = location_elem.text.strip() if location_elem else "Location not found"

                
                if not City or not Company or not Description:
                      print("Incomplete job information. Skipping this job.")
                      continue
                  
                  
                # Prepare job data
                job_data = {
                    "JobTitle": Title,
                    "Description": Description,
                    "DatePosted": Date,
                    "SeniorityLevel": Seniority_level,
                    "EmploymentType": Employment_type,
                    "Company": Company,
                    "City": City,
                    "URL": URL
                }

                # Post job data to API
                response = requests.post("https://localhost:7270/api/LinkedInModels/fdtjgz8r", json=job_data, verify=False)
                if response.status_code == 201:
                    print(f"Job successfully added: {Title}")
                    new_jobs_found = True
                else:
                    print(f"Failed to add job: {response.status_code} - {response.text}")

            except Exception as e:
                print(f"An error occurred while processing job details: {e}")

        # Determine if new jobs have been loaded
        if not new_jobs_found:
            # Try clicking the "Show more jobs" button only if no new jobs were found
            button_clicked = False
            try:
                show_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="See more jobs"]'))
                )
                show_more_button.click()
                button_clicked = True
                time.sleep(2)
            except Exception as e:
                print(f"No 'Show more' button found or could not click it: {e}")

            if button_clicked:
                # Re-check the job count after clicking
                current_job_count = len(driver.find_elements(By.CSS_SELECTOR, 'ul.jobs-search__results-list li'))
                if current_job_count > initial_job_count:
                    # Reset attempts if new jobs are found
                    attempts = 0
                else:
                    # If no new jobs found after clicking, increase attempts
                    attempts += 1
                    if attempts >= max_attempts:
                        print("Maximum attempts reached. Refreshing the page.")
                        driver.refresh()
                        time.sleep(5)  # Wait for the page to reload
                        # Re-load the jobs
                        continue
                    else:
                        # Scroll down to try and trigger more jobs
                        driver.execute_script("window.scrollBy(0, window.scrollY + 200);")
                        time.sleep(2)  # Wait for more jobs to load
            else:
                # If no button was clicked, just scroll down to see if more jobs are loaded
                driver.execute_script("window.scrollBy(0, window.scrollY + 200);")
                time.sleep(2)  # Wait for more jobs to load
        else:
            # Reset attempts if new jobs are found
            attempts = 0

def main():
    try:
        # Set up Chrome options to use incognito mode
        options = uc.ChromeOptions()

        driver = uc.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        dff = pd.DataFrame(columns=['Job Title', 'Description', 'Date Posted', 'Seniority Level', 'Employment Type', 'Company', 'City', 'URL'])
        process_page(driver, dff)
        driver.close()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
