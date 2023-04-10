from datetime import datetime
from electricity_usage_collector import usage_row_filter, usage_row_to_date

def test_usage_row_filter():
    collection_datetime = datetime.strptime('2023-04-06', '%Y-%m-%d')
    input = """\
MPRN,Meter Serial Number,Read Value,Read Type,Read Date and End Time
10305914213,31774820,0.174000,Active Import Interval (kW),05-04-2023 01:30
10305914213,31774820,0.174000,Active Import Interval (kW),06-04-2023 01:30
10305914213,31774820,0.174000,Active Import Interval (kW),07-04-2023 01:30"""
    expected = """\
MPRN,Meter Serial Number,Read Value,Read Type,Read Date and End Time
10305914213,31774820,0.174000,Active Import Interval (kW),06-04-2023 01:30"""
    expected_catchup = """\
MPRN,Meter Serial Number,Read Value,Read Type,Read Date and End Time
10305914213,31774820,0.174000,Active Import Interval (kW),05-04-2023 01:30
10305914213,31774820,0.174000,Active Import Interval (kW),06-04-2023 01:30"""
    assert usage_row_filter(input, collection_datetime) == expected
    assert usage_row_filter(input, collection_datetime, catchup=True) == expected_catchup
    
    
def test_usage_row_to_date():
    collection_datetime = datetime.strptime('2023-04-06', '%Y-%m-%d')
    row = "10305914213,31774820,0.174000,Active Import Interval (kW),06-04-2023 01:30"
    assert usage_row_to_date(row) == collection_datetime
    
    
    