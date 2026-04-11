import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup the browser
options = webdriver.ChromeOptions()
options.add_argument("window-size=1400,800")

driver = webdriver.Chrome(options=options)

# Navigate to the Dott login page
driver.get("https://app.dott.com/login")

# Find and fill in the login form
username_input = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//input[@name='email']"))
)

password_input = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//input[@name='password']"))
)

username_input.send_keys("your_email")
password_input.send_keys("your_password")

# Submit the login form
login_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
)

login_button.click()

# Navigate to the scooter rentals page
driver.get("https://app.dott.com/rent-scooter")

# Loop indefinitely to keep renting and returning scooters
while True:
    # Find and click the "rent" button
    rent_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@data-test='rent-button']"))
    )

    rent_button.click()

    # Wait for the scooter details to load
    scooter_details = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[@data-test='scooter-details']"))
    )

    # Get the estimated ride time from the scooter details
    estimated_ride_time = int(scooter_details.find_element(By.XPATH, ".//span[@data-test='ride-time']").text.split()[0])

    # If the estimated ride time is under the limit, terminate the ride
    if estimated_ride_time < 60:
        return_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-test='terminate-ride-button']"))
        )

        return_button.click()
    else:
        # If the estimated ride time is above the limit, wait for the full ride time
        time.sleep(estimated_ride_time * 60)

    # Terminate the ride prematurely
    return_button.click()
