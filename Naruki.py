import datetime
import os
from bs4 import BeautifulSoup
from lxml import etree as et
from csv import writer
import numpy as np
import pandas as pd
from selenium import webdriver

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

job_search_keyword = [' Data+Scientist', 'Business+Analyst', 'Data+Engineer', 'Python+Developer', 'Full+Stack+Developer', 'Machine+Learning+Engineer']
location_search_keyword = ['New+York', 'California', 'Los+Angeles']

chrome_options = Options()

def main():
  dff = pd.DataFrame(columns=['Job Title','Description', 'Experience Reqd', 'Company', 'City', 'Salary Range', 'Date Posted', 'URL'])
  driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

  url = "https://www.naukri.com/jobs-in-india"
  # Observation: Page1: https://www.naukri.com/it-jobs?k=it Page2: https://www.naukri.com/it-jobs-2
  driver.get(url)


  time.sleep(3)
  try: 
    driver.find_element(By.XPATH, '//*[@id="root"]/div[4]/div[1]/div/section[2]/div[1]/div[2]/span/span[2]/p').click()
    driver.find_element(By.XPATH, '//*[@id="root"]/div[4]/div[1]/div/section[2]/div[1]/div[2]/span/span[2]/ul/li[2]').click()
  except Exception as e:
    pass

  # time.sleep(3)
  pages = np.arange(1,250)

  for pages in pages:
    soup = BeautifulSoup(driver.page_source,'html5lib')
    results = soup.find(id='listContainer')
    job_elems = results.find_all('div', class_='srp-jobtuple-wrapper')
    for job_elem in job_elems:
      # Post Title
      T = job_elem.find('a',class_='title')
      Title=T.text

      # Description
      try:
        D = job_elem.find('span', class_='job-desc')
        Description = D.text
      except Exception as e:
        Description = None
      
      # Experience  
      E = job_elem.find('span', class_='expwdth')
      if E is None:
        Exp = "Not-Mentioned"
      else:
        Exp = E.text
      
      # Company
      C = job_elem.find('a', class_='comp-name')
      Company=C.text
      
      # City
      try:
        C = job_elem.find('span', class_='locWdth')
        City=C.text
      except Exception as e:
        City = None

      # Salary Range
      try:
        S = job_elem.find('span', 'ni-job-tuple-icon ni-job-tuple-icon-srp-rupee sal')
        Salary=S.text
        print("Salary: ", Salary)
      except Exception as e:
        Salary = "Not-Mentioned"
        print("Salary Not Found")

      # Date Posted
      D = job_elem.find('span', class_='job-post-day')
      try: 
        if D == 'Just Now':
          Date = 'Today'
        else:
          Date=D.text
      except Exception as e:
        Date = None      
      
      U = job_elem.find('a',class_='title').get('href')
      URL = U

      dff = pd.concat([dff, pd.DataFrame([[Title, Description, Exp, Company, City, Salary, Date, URL]], columns = ['Job Title','Description', 'Experience Reqd', 'Company', 'City', 'Salary Range', 'Date Posted', 'URL'])], ignore_index=True)
      print(dff)

      dff.to_excel(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', "NaukriJobListing_" + str(datetime.date.today()) + ".xlsx"), index=False)

    driver.execute_script("window.scrollTo(0,(document.body.scrollHeight) - 1500)")

    time.sleep(0.75)

    driver.find_element(By.XPATH, '//*[@id="lastCompMark"]/a[2]/span').click()

    time.sleep(3)

  print("*********************CONCLUSION: FINISHED FETCHING DATA FROM NAUKRI.COM*********************")

  # Closing the Driver
  driver.close()

main()

