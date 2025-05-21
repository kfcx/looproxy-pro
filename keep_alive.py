# keep_alive.py
import time
from curl_cffi import requests
import os
import threading

def function_to_run():
    count = 0
    url = f"{os.environ.get('PROJECT_DOMAIN')}/health"
    while True:
        if count > 30:
            break
        try:
            requests.get(url)
            print("Keeping alive...")
        except:
            print("Failed to keep alive")
            count += 1
        time.sleep(int(os.environ.get('SLEEPSECOND', 100)))

thread = threading.Thread(target=function_to_run)
thread.start()
# thread.join()
