import time
import logging
import argparse
from datetime import date
from datetime import datetime
from datetime import timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import os

# HDF file returns usage data since installation of smart meter until the last available time (~12 hours ago)
# Usage approach:
# Every day:
# 1. Collect usage up until two-days-ago
# 2. Append two-day-ago usage

# Create the parser
parser = argparse.ArgumentParser(description="Collects electricity usage", epilog="Usage: electricity_usage_extraction.py -u bob@gmail.com -p mypassword")

# Add arguments
parser.add_argument('-d', '--date', default=(date.today() - timedelta(days = 2)).strftime("%Y-%m-%d"), help='The collection date')
parser.add_argument('-u', '--username', help='Username')
parser.add_argument('-p', '--password', help='Password')

#TODO: make this more generic
file_path = r"C:\Users\Joao\Downloads"

# Parse the arguments
args = parser.parse_args()
username = args.username 
password = args.password
collection_date_string = args.date

# Validate collection date (must be at least 2 days ago)
parsed_date = datetime.strptime(collection_date_string, '%Y-%m-%d').date()
if parsed_date > (date.today() - timedelta(days = 2)):
    logging.error('date must at least 2 days ago')
    raise ValueError('date must at least 2 days ago')
    
start_date = parsed_date  # e.g. 2023-04-06 
end_date = parsed_date + timedelta(days = 1) # e.g. 2023-04-07 

# Installation steps
# 1. Download and install Chrome driver from https://sites.google.com/chromium.org/driver/home 
# 2. Install selenium `pip install selenium`
# 3. Instantiate webdriver.Crome() using the path to chromdriver 

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

logging.info(f"arg date: {args.date}")
logging.info(f"parsed date: {str(parsed_date)}")
logging.info(f"start_date: {start_date}")
logging.info(f"end_date: {end_date}")

service = Service(r'C:\Users\Joao\Downloads\chromedriver')
driver = webdriver.Chrome(service=service)
wait = WebDriverWait(driver, 30)
driver.get('https://www.esbnetworks.ie')
logging.info("Accepting cookies")
wait.until(EC.visibility_of_element_located((By.ID, "onetrust-accept-btn-handler"))).click()
logging.info("Accepted cookies")
time.sleep(10)
logging.info("Selecting Log in")
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "esb-navbar__navigation-base__login"))).click()
logging.info("Selected Log in")
logging.info("Opening Login page")
logging.info("Filling in username")
username_box = wait.until(EC.visibility_of_element_located((By.ID, "signInName")))
time.sleep(1)
username_box.send_keys(username)
logging.info("Filled in username")
logging.info("Filling in password")
wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(password)
logging.info("Filled in password")

logging.info("Clicking Login button")
wait.until(EC.visibility_of_element_located((By.ID, "next"))).click()
logging.info("Clicked Login button")

logging.info("Selecting My energy consumption")
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "icon-dataconsumption"))).click()
logging.info("Selected My energy consumption")

download_hdf = wait.until(EC.visibility_of_element_located((By.ID, "download-hdf")))
logging.info("Scrolling to download element")
download_hdf.send_keys("")
time.sleep(3)
logging.info("Downloading HDF")
download_hdf.click()
time.sleep(10)
# TODO: Wait until HDF is in Downloads
file_name = [f for f in os.listdir(file_path) if f.startswith("HDF")][0]
logging.info(f"Downloaded HDF")
# Get HDF from Downloads
file = os.path.join(file_path, file_name)
with open(file, "r") as f:
    # read the contents of the file
    file_contents = f.read()
# TODO: Filter earlier dates from file contents
filtered_usage = [r for r in file_contents.split('\n') if start_date.strftime("%d-%m-%Y") in r]
logging.info('\n'.join(filtered_usage))
os.remove(file)

# TODO: Persist HDF data
logging.info(f"Completed")
driver.close()