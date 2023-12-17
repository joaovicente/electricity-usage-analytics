import time
import logging
import argparse
import os
import platform
import boto3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    def __init__(self, username, password, storage_path, dry_run, runtime_mode):
        self.username = username
        self.password = password
        self.storage_path = storage_path
        self.runtime_mode = runtime_mode
        self.collected_csv_data = None
        self.last_updated_datetime = None
        self.last_collected_datetime = None
        os_name = platform.system()
        logging.info(f"runtime_mode: {runtime_mode}")
        logging.info(f"dry_run: {dry_run}")
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
            self.download_file_path = '/var/task'
            chrome_driver_path = '/opt/chromedriver'
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

    def bucket_and_path(self):
        path_parts = self.storage_path.split('/')
        bucket_name = path_parts[2]
        s3_path = '/'.join(path_parts[3:])
        return bucket_name, s3_path

    def list_s3_objects(self):
        # "s3://{bucket_name}/{s3_path}"
        # s3://jdvhome-dev-data/raw-landing/energia/usage-timeseries
        s3 = boto3.client('s3')
        bucket_name, s3_path = self.bucket_and_path()
        files = []
        # FIXME: pagination not implemented yet (only required when more than 1000 files in bucket)
        # pages_left = True
        # continuation_token = None
        # while pages_left:
        #    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_path, MaxKeys=1000, ContinuationToken=continuation_token)
        #    files.extend([e['Key'].split('/')[-1] for e in response.get('Contents', [])])
        #    pages_left = response.get('IsTruncated')
        #    continuation_token = response.get('NextContinuationToken')
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_path, MaxKeys=1000)
        files.extend([e['Key'].split('/')[-1] for e in response.get('Contents', [])])
        return files

    def retireve_last_updated_datetime(self):
        # detection of latest data collected from file/object name HDF-2023-01-02T2330.csv
        if self.storage_path.startswith("s3://"):
            persisted_files = self.list_s3_objects()
        elif os.path.exists(self.storage_path):
            persisted_files = os.listdir(self.storage_path)
        else:
            raise RuntimeError(f"retireve_last_updated_datetime Invalid or inexistent storage path: {self.storage_path}")
        if len(persisted_files) > 0:
            latest_file = persisted_files[-1]
            logging.info(f"latest file persisted was {latest_file}")
            self.last_updated_datetime = datetime.strptime(latest_file, "HDF-%Y-%m-%dT%H%M.csv")
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
        logging.info("Downloaded HDF")
        logging.info("Web collection completed")
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
        logging.info("Removing downloaded HDF file")
        os.remove(file)
        logging.info("Removed downloaded HDF file")

    def collected_row_datetime_not_persisted(self, row: str) -> datetime:
        # Sample CSV line
        # 10305914213,31774820,0.174000,Active Import Interval (kW),05-04-2023 01:30
        columns = row.split(',')
        if len(columns) != 5:
            raise ValueError(f"Unexpected number of columns in HDF row: {len(columns)}: {columns}")
        row_datetime = columns[-1]
        parsed_datetime = datetime.strptime(row_datetime, "%d-%m-%Y %H:%M")
        if self.last_collected_datetime is None:
            self.last_collected_datetime = parsed_datetime
        elif parsed_datetime > self.last_collected_datetime:
            self.last_collected_datetime = parsed_datetime
        logging.debug(f"usage_row_to_datetime parsed datetime: {parsed_datetime}")
        return self.last_updated_datetime is None or parsed_datetime > self.last_updated_datetime

    def filter_data_already_persisted(self) -> str:
        list_of_rows = self.collected_csv_data.splitlines()
        new_rows = [r for r in list_of_rows[1:] if self.collected_row_datetime_not_persisted(r)]
        data_to_be_persisted = [list_of_rows[0]] + new_rows
        return '\n'.join(data_to_be_persisted)

    def generate_filename(self):
        # HDF-2022-12-30T2330.csv
        return self.last_collected_datetime.strftime("HDF-%Y-%m-%dT%H%M.csv")

    def persist_in_filesystem(self, filename, data_to_be_persisted):
        file_path = os.path.join(self.storage_path, filename)
        with open(file_path, "w") as file:
            file.write(data_to_be_persisted)

    def persist_in_s3(self, filename, data_to_be_persisted):
        s3 = boto3.client('s3')
        bucket_name, s3_path = self.bucket_and_path()
        key = s3_path + '/' + filename
        s3.put_object(Bucket=bucket_name, Key=key, Body=data_to_be_persisted)

    def persist_collected_data(self):
        # persist only data not previously persisted
        data_to_be_persisted = self.filter_data_already_persisted()
        filename = self.generate_filename()
        data_to_be_persisted_rows = data_to_be_persisted.splitlines()
        row_count = len(data_to_be_persisted_rows)
        if self.storage_path is not None:
            if row_count > 1:
                logging.info(f"Persisting {filename} with {row_count} HDF rows in {self.storage_path}")
                if row_count > 0:
                    logging.info(f"line 1: {data_to_be_persisted_rows[0]}")
                if row_count > 1:
                    logging.info(f"line 2: {data_to_be_persisted_rows[1]}")
                if row_count > 0:
                    logging.info(f"last line: {data_to_be_persisted_rows[-1]}")
                if self.storage_path.startswith("s3://"):
                    self.persist_in_s3(filename, data_to_be_persisted)
                elif os.path.exists(self.storage_path):
                    self.persist_in_filesystem(filename, data_to_be_persisted)
            else:
                logging.info("No new data available for collection")
                data_to_be_persisted = None
                filename = None
        return filename, data_to_be_persisted


def parse_cli_args():
    # Create the parser
    parser = argparse.ArgumentParser(description="Collects electricity usage", epilog="Usage: electricity_usage_extraction.py -u bob@gmail.com -p mypassword")
    # Add arguments
    parser.add_argument('-u', '--username', default=os.environ.get('USERNAME', None), help='Username')
    parser.add_argument('-p', '--password', default=os.environ.get('PASSWORD', None), help='Password')
    parser.add_argument('-s', '--storage-path', default=os.environ.get('STORAGE_PATH', None),
                        help='Path where collected data will be stored. examples: /local/path, ./relative/path, s3://bucket/prefix')
    parser.add_argument('-d', '--dry-run', default=os.environ.get('DRY_RUN', False) == 'true', action='store_true',
                        help='Collect data but do not store it. Used for testing')
    # Parse the arguments
    args = parser.parse_args()
    return args.username, args.password, args.storage_path, args.dry_run


# Runtime modes:
class RuntimeMode(Enum):
    TEST = 1  # Testing using electricity_usage_collector_test
    LOCAL_WINDOWS = 2  # Testing collection using local chrome browser (Windows)
    DOCKER = 3  # 3. Collection in docker container


def detect_runtime_mode():
    os_name = platform.system()
    running_in_docker = os.environ.get('LAMBDA_TASK_ROOT', 'none') != 'none'
    if __name__ != '__main__':
        runtime_mode = RuntimeMode.TEST
    elif __name__ == '__main__' and os_name == 'Windows':
        runtime_mode = RuntimeMode.LOCAL_WINDOWS
    elif __name__ == '__main__' and os_name == 'Linux' and running_in_docker:
        runtime_mode = RuntimeMode.DOCKER
    else:
        raise RuntimeError(f"Unknown runtime mode: os: {os_name}, __main__: {__name__}, running_in_docker: {running_in_docker}")
    return runtime_mode


runtime_mode = detect_runtime_mode()
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

if runtime_mode != RuntimeMode.TEST:
    username, password, storage_path, dry_run = parse_cli_args()
    collector = ElectricityUsageCollector(username=username,
                                          password=password,
                                          storage_path=storage_path,
                                          dry_run=dry_run,
                                          runtime_mode=runtime_mode)
    collector.retireve_last_updated_datetime()
    collector.collect()
    if dry_run:
        logging.info("Dry run. Not persisting collected data")
    else:
        collector.persist_collected_data()
