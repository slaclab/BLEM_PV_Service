import os, requests
from datetime import datetime


# Get the Archiver Tool's URL
base_url = os.getenv("PYDM_ARCHIVER_URL")
base_url += "/retrieval/data/getData.json"

# Define the archived PV you want to get data on
archived_pv = "BLEM:SYS0:1:CU_SXR:LIVE:TWISS"

# Get desired date and time (using current in example)
from_dt = datetime.utcnow()
to_dt = datetime.utcnow()

# Format datetime strings
# 'Z' specifies the timezone (zero-offset)
# The local timezone would be '-08:00'
from_date_str = from_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
to_date_str = to_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

# Make the HTTP request using the parameters we defined
payload = requests.get(base_url, params={"pv": archived_pv,
                                         "from": from_date_str, 
                                         "to": to_date_str})

# Get the JSON data from the HTTP response
payload_json = payload.json()
data = payload_json[0]['data']
