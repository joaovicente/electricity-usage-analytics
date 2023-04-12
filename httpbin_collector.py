from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import logging
import os
import time
import platform
from tempfile import mkdtemp

os_name = platform.system()
if os_name == 'Windows':
    download_file_path = rf'C:\Users\{os.environ.get("USERNAME")}\Downloads'
    chrome_driver_path = rf'C:\Users\{os.environ.get("USERNAME")}\Downloads\chromedriver'
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service)
else:
    download_file_path = rf'/var/task'
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
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
def is_running_in_docker():
    """Check if the code is running inside a Docker container."""
    cgroup_file = "/proc/self/cgroup"
    return os.path.exists(cgroup_file) and any("docker" in line for line in open(cgroup_file))
    
    
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
wait = WebDriverWait(driver, 30)
url = 'https://httpbin.org/#/Response_formats/get_json'
logging.info(f"Opening {url} page on {os_name}, __name__: {__name__}, docker execution: {is_running_in_docker()}")
driver.get(url)
logging.info(f"Clicking on GET /json")
wait.until(EC.visibility_of_element_located((By.ID, "operations-Response formats-get_json"))).click()
logging.info(f"Clicking on Try out button")
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "try-out__btn"))).click()
logging.info(f"Clicking on Execute button")
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "execute"))).click()
logging.info(f"Clicking on Download button")
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "download-contents"))).click()

time.sleep(5)
downloaded_files = [f for f in os.listdir(download_file_path) if f.startswith("response")]
if len(downloaded_files) > 0:
    logging.info(f"{downloaded_files[0]} found in {download_file_path}")

file_path = os.path.join(download_file_path, downloaded_files[0])
logging.info(f"deleting {file_path}")
os.remove(file_path)

driver.close()