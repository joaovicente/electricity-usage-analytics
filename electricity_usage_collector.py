import time
import logging
import argparse
import os
import platform
from datetime import date
from datetime import datetime
from datetime import timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from tempfile import mkdtemp
from enum import Enum

# HDF file returns usage data since installation of smart meter until the last available time (~12 hours ago)
# Usage approach:
# Every day:
# 1. Collect usage up until two-days-ago if in catchup mode or just the two-days-ago day if not in catchup mode
# 2. Append usage to output

# Installation steps
# 1. Download and install Chrome driver from https://sites.google.com/chromium.org/driver/home (script assumes it is installed in your Downloads folder)
# 2. Install selenium `pip install selenium`
# 3. Instantiate webdriver.Crome() using the path to chromdriver 

class ElectricityUsageCollector():
    def __init__(self, username, password, runtime_mode):
        self.username = username
        self.password = password
        self.runtime_mode = runtime_mode
        self.collected_csv_data = None
        self.last_updated_datetime = None
        self.last_collected_datetime = None
        os_name = platform.system()
        if os_name == 'Windows':
            self.download_file_path = rf'C:\Users\{os.environ.get("USERNAME")}\Downloads'
            chrome_driver_path = rf'C:\Users\{os.environ.get("USERNAME")}\Downloads\chromedriver'
            options = None
        elif os_name == 'Linux':
            self.download_file_path = rf'/var/task'
            chrome_driver_path = rf'/opt/chromedriver'
            options = webdriver.ChromeOptions()
            options.binary_location = '/opt/chrome/chrome'
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1280x1696")
            options.add_argument("--single-process")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-dev-tools")
            options.add_argument("--no-zygote")
            options.add_argument(f"--user-data-dir={mkdtemp()}")
            options.add_argument(f"--data-path={mkdtemp()}")
            options.add_argument(f"--disk-cache-dir={mkdtemp()}")
            options.add_argument("--remote-debugging-port=9222")
        else:
            raise ValueError(f"Unexpected os {os_name}")
        if runtime_mode != RuntimeMode.TEST:
            service = Service(chrome_driver_path)
            driver = webdriver.Chrome(service=service, options=options)
        
    def simulate_last_updated_datetime(self, last_updated_datetime: datetime):
        # Use this function only for testing purposes
        # last_updated_datetime is None to simulate no previous collection data persisted
        # last_updated_datetime is datetime to simulate previous collection data persisted
        if last_updated_datetime is not None and not isinstance(last_updated_datetime, datetime):
            raise ValueError("simulate_last_updated_datetime parameter must be a datetime")
        if self.runtime_mode != RuntimeMode.TEST:
            raise RuntimeError("simulate_last_updated_datetime only supported in test mode")
        self.last_updated_datetime = last_updated_datetime
    
    def retireve_last_updated_datetime(self):
        # TODO: Implement detection of latest data collected from file/object name HDF-2023-01-02T2330.csv 
        return self.last_updated_datetime
        
    def simulate_collection(self, csv_data: str):
        # Use this function only for testing purposes
        if self.runtime_mode != RuntimeMode.TEST:
            raise RuntimeError("simulate_collection only supported in test mode")
        self.collected_csv_data = csv_data
        
    def collect(self):
        # TODO: Implement collection
        logging.warning("collect() not implemented")
  
    def collected_row_datetime_not_persisted(self, row: str) -> datetime:
        # Sample CSV line
        # 10305914213,31774820,0.174000,Active Import Interval (kW),05-04-2023 01:30
        columns = row.split(',')
        if len(columns) != 5:
            raise ValueError(f"Unexpected number of columns in HDF row: {len(columns)}: {columns}") 
        row_datetime = columns[-1]
        parsed_datetime = datetime.strptime(row_datetime, "%d-%m-%Y %H:%M")
        if self.last_collected_datetime == None:
            self.last_collected_datetime = parsed_datetime
        elif parsed_datetime > self.last_collected_datetime:
            self.last_collected_datetime = parsed_datetime
        logging.debug(f"usage_row_to_datetime parsed datetime: {parsed_datetime}")
        return self.last_updated_datetime == None or parsed_datetime > self.last_updated_datetime

    def filter_data_already_persisted(self):
        list_of_rows = self.collected_csv_data.splitlines()
        new_rows = [r for r in list_of_rows[1:] if self.collected_row_datetime_not_persisted(r)]
        data_to_be_persisted = [list_of_rows[0]] + new_rows
        return '\n'.join(data_to_be_persisted)
        
    def generate_filename(self):
        # HDF-2022-12-30T2330.csv
        return self.last_collected_datetime.strftime("HDF-%Y-%m-%dT%H%M.csv")
    
    def persist_collected_data(self):
        # persist only data not previously persisted
        data_to_be_persisted = self.filter_data_already_persisted()
        filename = self.generate_filename()
        if self.runtime_mode != RuntimeMode.TEST:
            #TODO: Store collection data
            logging.warning("persist_collected_data() not implemented")
        return filename, data_to_be_persisted

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

# Runtime modes:
class RuntimeMode(Enum):
    TEST = 1 # Testing using electricity_usage_collector_test
    LOCAL_WINDOWS = 2 # Testing collection using local chrome browser (Windows)
    DOCKER = 3 # 3. Collection in docker container
    
def detect_runtime_mode():
    os_name = platform.system()
    cgroup_file = "/proc/self/cgroup"
    running_in_docker = os.path.exists(cgroup_file) and any("docker" in line for line in open(cgroup_file))
    if __name__ != '__main__':
        runtime_mode = RuntimeMode.TEST
    elif __name__ == '__main__' and os_name == 'Windows':
        runtime_mode = RuntimeMode.LOCAL_WINDOWS
    elif __name__ == '__main__' and os_name == 'Linux' and running_in_docker:
        runtime_mode = RuntimeMode.DOCKER
    else:
        raise RuntimeError("Unknown runtime mode")
    return runtime_mode
    
runtime_mode = detect_runtime_mode()
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logging.info(f"Runtime Mode: {runtime_mode}")

if runtime_mode != RuntimeMode.TEST:
    print(f"Runtime Mode: {runtime_mode}")
    username, password, date, catchup = parse_cli_args()
    collector = ElectricityUsageCollector(username, password, runtime_mode)
    collector.retireve_last_updated_datetime()
    collector.collect()
    collector.persist_collected_data()

#if False and not testing() and input_valid(username, password, date, catchup):
    #parsed_date = datetime.strptime(date, '%Y-%m-%d')
    #extract_from_web_site(username, password)
    #process_hdf_file(parsed_date, catchup)
    #persist_hdf_file_contents()