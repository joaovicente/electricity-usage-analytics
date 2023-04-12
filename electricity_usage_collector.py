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
        logging.info(f"runtime_mode: {runtime_mode}")
        logging.info(f"username: {username}")
        if username is None:
            raise ValueError('username is None')
        if password is None:
            raise ValueError('password is None')
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
            self.driver = webdriver.Chrome(service=service, options=options)
            
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
        wait = WebDriverWait(self.driver, 30)
        self.driver.get('https://www.esbnetworks.ie')
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
        username_box.send_keys(self.username)
        logging.info("Filled in username")
        logging.info("Filling in password")
        wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(self.password)
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
        self.driver.close()
        
        logging.info("Processing HDF file")
        # TODO: Wait until HDF is in Downloads
        hdf_files = [f for f in os.listdir(self.download_file_path) if f.startswith("HDF")]
        num_files_found = len(hdf_files) 
        if num_files_found != 1:
            raise ValueError(f"Found {num_files_found} HDF files in {self.download_file_path}")
        file = os.path.join(self.download_file_path, hdf_files[0])
        logging.info(f"Processing HDF file: {file}")
        # Get HDF from Downloads
        with open(file, "r") as f:
            # read the contents of the file
            file_contents = f.read()
        self.collected_csv_data = file_contents
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
        logging.info(f"Removing HDF file")
        os.remove(file)
        logging.info(f"Removed HDF file")
  
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
        data_to_be_persisted_rows = data_to_be_persisted.splitlines()
        row_count = len(data_to_be_persisted_rows)
        logging.info(f"Persisting {row_count} HDF rows in {filename}")
        if row_count > 0: logging.info(f"line 1: {data_to_be_persisted_rows[0]}") 
        if row_count > 1: logging.info(f"line 2: {data_to_be_persisted_rows[1]}") 
        if row_count > 0: logging.info(f"last line: {data_to_be_persisted_rows[-1]}") 
        return filename, data_to_be_persisted

def parse_cli_args():
    # Create the parser
    parser = argparse.ArgumentParser(description="Collects electricity usage", epilog="Usage: electricity_usage_extraction.py -u bob@gmail.com -p mypassword")
    # Add arguments
    parser.add_argument('-u', '--username', help='Username')
    parser.add_argument('-p', '--password', help='Password')
    # Parse the arguments
    args = parser.parse_args()
    return args.username, args.password
    
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

if runtime_mode != RuntimeMode.TEST:
    username, password = parse_cli_args()
    collector = ElectricityUsageCollector(username, password, runtime_mode)
    collector.retireve_last_updated_datetime()
    collector.collect()
    collector.persist_collected_data()