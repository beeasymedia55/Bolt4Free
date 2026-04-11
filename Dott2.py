import time
import requests

def ride_free():
    start_url = "https://api.dott.com/android/v2/riding-params"
    end_rides_url = "https://api.dott.com/android/v2/rides"

    # Assume the electrode is being initialized
    riding_params = {
        "location": {
            "lat": 37.7749,
            "lng": -122.4194
        }
    }

    headers = {
        "content-type": "application/json",
        "accept": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
    }

    while True:
        response = requests.post(start_url, json=riding_params, headers=headers)
        if response.status_code == 200:
            ride_id = response.json()["ride_id"]
            print(f"Started ride with ID {ride_id}")
            time.sleep(5)  # ride for at least 5 seconds to exceed free time threshold
            requests.delete(f"{end_rides_url}/{ride_id}", headers=headers)
            print("Terminated ride")
        else:
            print("Failed to start a ride. Trying again...")
        time.sleep(60)  # Wait 60 seconds before attempting the next free ride

if __name__ == "__main__":
    ride_free()
