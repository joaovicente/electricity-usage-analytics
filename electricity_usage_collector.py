import time
import logging
import argparse
import os
from datetime import date
from datetime import datetime
from datetime import timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# HDF file returns usage data since installation of smart meter until the last available time (~12 hours ago)
# Usage approach:
# Every day:
# 1. Collect usage up until two-days-ago if in catchup mode or just the two-days-ago day if not in catchup mode
# 2. Append usage to output

# Installation steps
# 1. Download and install Chrome driver from https://sites.google.com/chromium.org/driver/home (script assumes it is installed in your Downloads folder)
# 2. Install selenium `pip install selenium`
# 3. Instantiate webdriver.Crome() using the path to chromdriver 


#TODO: make this more generic
download_file_path = rf'C:\Users\{os.environ.get("USERNAME")}\Downloads'
chrome_driver_path = rf'C:\Users\{os.environ.get("USERNAME")}\Downloads\chromedriver'

def parse_cli_args():
    # Create the parser
    parser = argparse.ArgumentParser(description="Collects electricity usage", epilog="Usage: electricity_usage_extraction.py -u bob@gmail.com -p mypassword -d 2023-04-06 --catchup")
    # Add arguments
    parser.add_argument('-d', '--date', default=(date.today() - timedelta(days = 2)).strftime("%Y-%m-%d"), help='The collection date')
    parser.add_argument('-u', '--username', help='Username')
    parser.add_argument('-p', '--password', help='Password')
    parser.add_argument('-c', '--catchup', action="store_true", default=False, help='Catchup mode gathers all usage up until date')
    # Parse the arguments
    args = parser.parse_args()
    return args.username, args.password, args.date, args.catchup
    
def input_valid(username, password, date, catchup):
    logging.info(f"date: {date}")
    logging.info(f"username: {username}")
    logging.info(f"catchup is : {catchup}")
    # Validate collection date (must be at least 2 days ago)
    parsed_date = datetime.strptime(date, '%Y-%m-%d')
    logging.info(f"parsed date: {str(date)}")
    if parsed_date > (datetime.today() - timedelta(days = 2)):
        logging.error('date must at least 2 days ago')
        raise ValueError('date must at least 2 days ago')
    if username is None:
        raise ValueError('username is None')
    if password is None:
        raise ValueError('password is None')
    return True

def extract_from_web_site(username, password):
    service = Service(chrome_driver_path)
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
    logging.info(f"Downloaded HDF")
    logging.info(f"Web collection completed")
    driver.close()
    
def process_hdf_file(date, catchup):
    logging.info("Processing HDF file")
    # TODO: Wait until HDF is in Downloads
    hdf_files = [f for f in os.listdir(download_file_path) if f.startswith("HDF")]
    num_files_found = len(hdf_files) 
    if num_files_found != 1:
        raise ValueError(f"Found {num_files_found} HDF files in {download_file_path}")
    file = os.path.join(download_file_path, hdf_files[0])
    logging.info(f"Processing HDF file: {file}")
    
    # FIXME: Detach file processing from web extraction and debug why filtering is not returing any results
    # Add info statements to help debugging when moving to docker, like:
    # name of file collected, number of rows in file, head and tail of file, and parsing information helping debug cross-platform issues (linux vs windows)
    
    # Get HDF from Downloads
    with open(file, "r") as f:
        # read the contents of the file
        file_contents = f.read()
    lines = file_contents.splitlines()
    len_lines = len(lines)
    if len_lines < 4:
        ValueError(f"HDF file only has {len_lines}")
    logging.info(f"HDF first two lines of {len_lines}:")
    logging.info(f"{lines[0]}")
    logging.info(f"{lines[1]}")
    logging.info("HDF last two lines:")
    logging.info(f"{lines[-2]}")
    logging.info(f"{lines[-1]}")
    
    filtered_csv = usage_row_filter(file_contents, date, catchup)
    filtered_csv_lines = filtered_csv.splitlines()
    len_filtered_csv_lines = len(filtered_csv_lines)
    logging.info(f"Filtered HDF lines of {len_filtered_csv_lines}:")
    if len_filtered_csv_lines > 0: logging.info(f"line 1: {filtered_csv_lines[0]}") 
    if len_filtered_csv_lines > 1: logging.info(f"line 2: {filtered_csv_lines[1]}") 
    if len_filtered_csv_lines > 0: logging.info(f"last line: {filtered_csv_lines[-1]}") 
    os.remove(file)
    

def usage_row_to_date(row: str) -> datetime:
    # Sample CSV line
    # 10305914213,31774820,0.174000,Active Import Interval (kW),05-04-2023 01:30
    columns = row.split(',')
    if len(columns) != 5:
        raise ValueError(f"Unexpected number of columns in HDF row: {len(columns)}") 
    datetime_column = columns[-1]
    datetime_split = datetime_column.split()
    if len(datetime_split) != 2:
        raise ValueError(f"Unexpected date time format: {datetime_column}") 
    date = datetime_split[0]
    parsed_date = datetime.strptime(date, "%d-%m-%Y")
    logging.debug(f"parsed date: {parsed_date}")
    return parsed_date

def filter_hdf_rows(orginal_list, date, catchup):
    if not isinstance(date, datetime):
        raise ValueError(f"filter_hdf_rows date must be a datetime - is {type(date)}")
    filtered_rows = []
    for row in orginal_list:
        row_date = usage_row_to_date(row)
        logging.debug(f"filter_hdf_rows row_date: {row_date} - {type(row_date)}")
        logging.debug(f"filter_hdf_rows date: {date} - {type(date)}")
        if catchup and row_date <= date:
            logging.debug(f"filter_hdf_rows match")
            filtered_rows.append(row)
        if not catchup and row_date == date:
            logging.debug(f"filter_hdf_rows match")
            filtered_rows.append(row)
    return filtered_rows
    

def usage_row_filter(usage_csv: str, collection_date: datetime, catchup: bool=False) -> str:
    usage_csv_as_list = usage_csv.splitlines()
    # FIXME: REMOVE LINE BELOW - DBUGGING ONLY
    #usage_csv_as_list = usage_csv_as_list[:100]
    logging.info(f"Filtering HDF file with {len(usage_csv_as_list)} rows for {collection_date.date()}")
    header_row = usage_csv_as_list.pop(0)
    filtered_list = filter_hdf_rows(usage_csv_as_list, collection_date, catchup)
    result = header_row + '\n' + '\n'.join(filtered_list)
    return result

def testing():
    # When execution from cli __name__ == __main__
    # When execution from pytest __name__ == __electricity_usage_collector__
    return __name__ != '__main__'
    
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logging.info(f"__name__: {__name__}")
username, password, date, catchup = parse_cli_args()
if not testing() and input_valid(username, password, date, catchup):
    parsed_date = datetime.strptime(date, '%Y-%m-%d')
    extract_from_web_site(username, password)
    process_hdf_file(parsed_date, catchup)
    #persist_hdf_file_contents()
    