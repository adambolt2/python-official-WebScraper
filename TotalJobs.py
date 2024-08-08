import os
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc

def post_job_data(job_data):
    try:
        # Post job data to the API with SSL verification disabled
        response = requests.post("https://localhost:7270/api/TotalJobsModels/fdtjgz8r", json=job_data, verify=False)
        if response.status_code == 201:
            print(f"Job successfully added: {job_data['Job Title']}")
        else:
            print(f"Failed to add job: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        print(f"An error occurred while posting job data: {e}")

def process_page(driver):
    soup = BeautifulSoup(driver.page_source, 'html5lib')
    job_elems = soup.find_all('article')

    if not job_elems:
        print("No job listings found on the current page.")
        return False  # No jobs found, signal to stop scraping

    for index, job_elem in enumerate(job_elems):
        try:
            # Extract job content
            job_content = job_elem.find('div', attrs={'data-testid': 'job-card-content'})
            
            # Extract job title
            title_elem = job_content.find('h2')
            Title = title_elem.text.strip() if title_elem else "Title not found"
            print(f"Found title: {Title}")
            
            base_url = 'https://www.totaljobs.com'
            URL = base_url + title_elem.find('a').get('href')
            print('URL FOUND AND CONSTRUCTED', URL)
            
            # Extract company name
            company_elem = job_content.find(attrs={'data-at': 'job-item-company-name'})
            Company = company_elem.text.strip() if company_elem else "Company not found"
            print(f"Company found: {Company}")

            # Extract salary info
            salary_elem = job_content.find(attrs={'data-at': 'job-item-salary-info'})
            Salary = salary_elem.text.strip() if salary_elem else "Not-Mentioned"
            print(f"Salary info found: {Salary}")

            # Extract location
            location_elem = job_content.find(attrs={'data-at': 'job-item-location'})
            Location = location_elem.text.strip() if location_elem else "Location not found"
            print(f"Location found: {Location}")

            # Use Selenium to find the button and click it
            try:
                expand_button = driver.find_element(By.XPATH, f"//article[{index+1}]//span[contains(@class, 'text-snippet-expand-button')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", expand_button)
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(expand_button))
                expand_button.click()
                print("Expand button clicked.")
                time.sleep(2)  # Wait for the description to load

                # After clicking the expand button, re-fetch the job elements from the updated page source
                soup_updated = BeautifulSoup(driver.page_source, 'html5lib')
                job_elem_updated = soup_updated.find_all('article')[index]
                
                # Extract the job description
                description_elem = job_elem_updated.find(attrs={'data-at': 'jobcard-content'})
                Description = description_elem.text.strip() if description_elem else "Description not found"
                Description = Description.replace('""', '').strip()
                print(f"Description found: {Description}")

            except NoSuchElementException:
                print("Expand button not found within job element.")
                Description = "Description not found"

            if not Location or not Company or not Description:
                print("Incomplete job information. Skipping this job.")
                continue
                  
            # Post job data to the API
            job_data = {
                "JobTitle": Title,
                "Description": Description,
                "Company": Company,
                "City": Location,
                "SalaryRange": Salary,
                "URL": URL
            }
            post_job_data(job_data)

        except Exception as e:
            print(f"An error occurred while processing job details: {e}")

    return True  # Jobs found, signal to continue scraping

def main():
    initial_url = "https://www.totaljobs.com/jobs/software-engineer/in-united-kingdom?whereType=autosuggest&radius=10&page=1"

    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--incognito")

    driver = uc.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(initial_url)
    
    # Accept cookies on the first page load
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'ccmgt_explicit_accept'))).click()
        print("Cookies button clicked.")
    except NoSuchElementException:
        print("Cookies button not found.")

    while True:
        try:
            has_jobs = process_page(driver)
            
            if not has_jobs:
                print("No more jobs found. Exiting.")
                break

            # Find the next page button using BeautifulSoup and Selenium
            try:
                soup = BeautifulSoup(driver.page_source, 'html5lib')
                chevron_right_icon = soup.find('svg', attrs={'data-genesis-element': 'ChevronRightIcon'})
                
                if chevron_right_icon:
                    parent_anchor = chevron_right_icon.find_parent('a')
                    next_page_href = parent_anchor.get('href')
                    if next_page_href:
                        next_page_button = driver.find_element(By.XPATH, f"//a[@href='{next_page_href}']")
                        driver.execute_script("arguments[0].scrollIntoView(true);", next_page_button)
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(next_page_button))
                        next_page_button.click()
                        print("Navigated to the next page.")
                        time.sleep(3)  # Wait for the next page to load
                    else:
                        print("Next page href not found. Exiting.")
                        break
                else:
                    print("Next page button not found. Exiting.")
                    break

            except NoSuchElementException:
                print("Next page button not found. Exiting.")
                break
            except TimeoutException:
                print("Timeout while waiting for the next page button to be clickable. Exiting.")
                break

        except Exception as e:
            print(f"An error occurred: {e}")
            break

    driver.quit()

if __name__ == "__main__":
    main()
