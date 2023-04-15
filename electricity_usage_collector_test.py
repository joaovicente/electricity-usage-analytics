from datetime import datetime
from datetime import timedelta
from electricity_usage_collector import ElectricityUsageCollector, RuntimeMode
import os
import shutil
import pytest

def mock_collection_data_as_list(start_datetime, end_datetime, fixed_usage=True):
    header = 'MPRN,Meter Serial Number,Read Value,Read Type,Read Date and End Time'
    data = []
    row_datetime = start_datetime
    usage = 1.000001
    while row_datetime <= end_datetime:
        if not fixed_usage:
            usage = usage + 0.000001
        row_datetime_as_string = row_datetime.strftime("%d-%m-%Y %H:%M")
        usage_as_string = "{:.6f}".format(usage)
        data.append(f"10305914213,31774820,{usage_as_string},Active Import Interval (kW),{row_datetime_as_string}")
        row_datetime = row_datetime + timedelta(minutes=30)
    data.reverse()
    return [header] + data
    
def test_electricity_usage_collector_first_collection():
    # First collection
    collector = ElectricityUsageCollector(username="username", password="password", storage_path=None, runtime_mode=RuntimeMode.TEST)
    collector.simulate_last_updated_datetime(None) # simulate no previous update
    collection_1 = mock_collection_data_as_list(
        datetime(year=2023, month=1, day=1, hour=0, minute=0), 
        datetime(year=2023, month=1, day=2, hour=23, minute=30))
    collector.simulate_collection('\n'.join(collection_1)) # 2023-01-01 to 2023-01-02
    filename, csv_data = collector.persist_collected_data()
    assert filename == "HDF-2023-01-02T2330.csv" # last persisted datetime
    assert csv_data.splitlines() == collection_1
    
def test_electricity_usage_collector_second_collection():
    # second collection
    collector = ElectricityUsageCollector(username="username", password="password", storage_path=None, runtime_mode=RuntimeMode.TEST)
     # simulate no previous update
    collector.simulate_last_updated_datetime(datetime(year=2023, month=1, day=2, hour=23, minute=30))
    collection_2 = mock_collection_data_as_list(
        datetime(year=2023, month=1, day=1, hour=0, minute=0), 
        datetime(year=2023, month=1, day=4, hour=23, minute=30))
    collector.simulate_collection('\n'.join(collection_2)) # 2023-01-01 to 2023-01-04
    filename, csv_data = collector.persist_collected_data()
    expected_persisted_data = mock_collection_data_as_list(
        datetime(year=2023, month=1, day=3, hour=0, minute=0), 
        datetime(year=2023, month=1, day=4, hour=23, minute=30))
    assert filename == "HDF-2023-01-04T2330.csv" # last persisted datetime
    assert csv_data.splitlines() == expected_persisted_data
   
def test_consecutive_day_collection(): 
    storage_path='./test_storage'
    if os.path.exists(storage_path):
        shutil.rmtree(storage_path)
    os.mkdir(storage_path)
    
    # first day 
    collector = ElectricityUsageCollector(username="username", password="password", storage_path=storage_path, runtime_mode=RuntimeMode.TEST)
    collector.retireve_last_updated_datetime()
    collection_1 = mock_collection_data_as_list(
        datetime(year=2023, month=1, day=1, hour=0, minute=0), 
        datetime(year=2023, month=1, day=2, hour=23, minute=30))
    collector.simulate_collection('\n'.join(collection_1))
    collector.persist_collected_data()
    
    # second day 
    collector = ElectricityUsageCollector(username="username", password="password", storage_path=storage_path, runtime_mode=RuntimeMode.TEST)
    collector.retireve_last_updated_datetime()
    collection_2 = mock_collection_data_as_list(
        datetime(year=2023, month=1, day=1, hour=0, minute=0), 
        datetime(year=2023, month=1, day=4, hour=23, minute=30))
    collector.simulate_collection('\n'.join(collection_2))
    collector.persist_collected_data()
    
    # second day - second collection
    collector = ElectricityUsageCollector(username="username", password="password", storage_path=storage_path, runtime_mode=RuntimeMode.TEST)
    collector.retireve_last_updated_datetime()
    collection_2 = mock_collection_data_as_list(
        datetime(year=2023, month=1, day=1, hour=0, minute=0), 
        datetime(year=2023, month=1, day=4, hour=23, minute=30))
    collector.simulate_collection('\n'.join(collection_2))
    filename, persisted_data = collector.persist_collected_data()
    assert filename == None
    assert persisted_data == None

def test_list_s3_objects():
    storage_path = "s3://jdvhome-dev-data/raw-landing/energia/usage-timeseries"
    collector = ElectricityUsageCollector(username="username", password="password", storage_path=storage_path, runtime_mode=RuntimeMode.TEST)
    if os.environ.get('AWS_ACCESS_KEY_ID', None) != None and os.environ.get('AWS_SECRET_ACCESS_KEY', None) != None:
        objects = collector.list_s3_objects()
        len(objects) > 0
    else:
        pytest.fail("AWS Credentials not defined as environment variables")
        