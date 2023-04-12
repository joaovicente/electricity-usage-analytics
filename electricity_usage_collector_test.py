from datetime import datetime
from datetime import timedelta
from electricity_usage_collector import ElectricityUsageCollector, RuntimeMode, usage_row_filter, usage_row_to_date

#def test_usage_row_filter():
#    collection_datetime = datetime.strptime('2023-04-06', '%Y-%m-%d')
#    input = """\
#MPRN,Meter Serial Number,Read Value,Read Type,Read Date and End Time
#10305914213,31774820,0.174000,Active Import Interval (kW),05-04-2023 01:30
#10305914213,31774820,0.174000,Active Import Interval (kW),06-04-2023 01:30
#10305914213,31774820,0.174000,Active Import Interval (kW),07-04-2023 01:30"""
#    expected = """\
#MPRN,Meter Serial Number,Read Value,Read Type,Read Date and End Time
#10305914213,31774820,0.174000,Active Import Interval (kW),06-04-2023 01:30"""
#    expected_catchup = """\
#MPRN,Meter Serial Number,Read Value,Read Type,Read Date and End Time
#10305914213,31774820,0.174000,Active Import Interval (kW),05-04-2023 01:30
#10305914213,31774820,0.174000,Active Import Interval (kW),06-04-2023 01:30"""
#    assert usage_row_filter(input, collection_datetime) == expected
#    assert usage_row_filter(input, collection_datetime, catchup=True) == expected_catchup
    
    
#def test_usage_row_to_date():
#    collection_datetime = datetime.strptime('2023-04-06', '%Y-%m-%d')
#    row = "10305914213,31774820,0.174000,Active Import Interval (kW),06-04-2023 01:30"
#    assert usage_row_to_date(row) == collection_datetime
    
def mock_collection_data_as_list(start_datetime, end_datetime, fixed_usage=True):
    data = []
    data.append('MPRN,Meter Serial Number,Read Value,Read Type,Read Date and End Time')
    row_datetime = start_datetime
    usage = 1.000001
    while row_datetime <= end_datetime:
        if not fixed_usage:
            usage = usage + 0.000001
        row_datetime_as_string = row_datetime.strftime("%d-%m-%Y %H:%M")
        usage_as_string = "{:.6f}".format(usage)
        data.append(f"10305914213,31774820,{usage_as_string},Active Import Interval (kW),{row_datetime_as_string}")
        row_datetime = row_datetime + timedelta(minutes=30)
    #print('\n'.join(data))
    return data
    
def test_electricity_usage_collector_first_collection():
    # First collection
    collector = ElectricityUsageCollector("username", "password", RuntimeMode.TEST)
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
    collector = ElectricityUsageCollector("username", "password", RuntimeMode.TEST)
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
    
    
    