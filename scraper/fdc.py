import json
import re

from datetime import datetime
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scraper.records import get_record_dict
from utils.readJson import get_address_data, strip_zip_code


def get_fdc_data(dr, headless=False):
    print("Scraping data from fresqueduclimat.org\n\n")

    options = FirefoxOptions()
    options.headless = headless

    driver = webdriver.Firefox(options=options, executable_path=dr)

    webSites = [
        {
            "url": "https://fresqueduclimat.org/inscription-atelier/grand-public/",
            "id": 200,
        }
    ]

    records = []

    for page in webSites:
        print(f"\n========================")
        driver.get(page["url"])
        driver.implicitly_wait(2)

        wait = WebDriverWait(driver, 10)
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe)

        ele = driver.find_elements(By.CSS_SELECTOR, "a.link-dark")
        links = [e.get_attribute("href") for e in ele]

        for link in links:
            print(f"\n-> Processing {link} ...")
            driver.get(link)
            driver.implicitly_wait(3)

            ################################################################
            # Parse event title
            ################################################################
            print("Parsing title...")

            title_el = driver.find_element(
                by=By.TAG_NAME,
                value="h3",
            )
            title = title_el.text

            ################################################################
            # Parse start and end dates
            ################################################################
            print("Parsing start and end dates...")

            clock_icon = driver.find_element(By.CLASS_NAME, "fa-clock")
            parent_div = clock_icon.find_element(By.XPATH, "..")
            event_time = parent_div.text

            month_mapping = {
                "janvier": 1,
                "février": 2,
                "mars": 3,
                "avril": 4,
                "mai": 5,
                "juin": 6,
                "juillet": 7,
                "août": 8,
                "septembre": 9,
                "octobre": 10,
                "novembre": 11,
                "décembre": 12,
            }

            date_and_times = event_time.split(",")
            day, month_string, year = date_and_times[0].split(" ")
            times = date_and_times[1].split(" de ")[1]

            # Define a regular expression pattern to extract times
            time_pattern = r"(\d{2}h\d{2}) à (\d{2}h\d{2})"

            # Find matches using the pattern
            matches = re.findall(time_pattern, times)
            if matches:
                start_time, end_time = matches[0]
            else:
                print("Rejecting record: bad format in dates")
                continue

            # Extract hours and minutes from time strings
            start_hour, start_minute = map(int, start_time.split("h"))
            end_hour, end_minute = map(int, end_time.split("h"))

            # Construct the datetime objects
            event_start_datetime = datetime(
                int(year),
                month_mapping[month_string],
                int(day),
                start_hour,
                start_minute,
            )
            event_end_datetime = datetime(
                int(year), month_mapping[month_string], int(day), end_hour, end_minute
            )

            ################################################################
            # Is it an online event?
            ################################################################
            online = True
            try:
                driver.find_element(By.CLASS_NAME, "fa-video")
            except NoSuchElementException:
                online = False

            ################################################################
            # Location data
            ################################################################
            if not online:
                pin_icon = driver.find_element(By.CLASS_NAME, "fa-map-pin")
                parent_div = pin_icon.find_element(By.XPATH, "..")
                full_location = parent_div.text

                if "," in full_location:
                    loc_arr = full_location.split(",")
                    if len(loc_arr) >= 5:
                        print(
                            f"Rejecting records: address is too long ({len(loc_arr)} parts)"
                        )
                        continue
                    elif len(loc_arr) >= 3:
                        if loc_arr[2].strip().lower() == "france":
                            address = loc_arr[0]
                            city = loc_arr[1]
                        else:
                            location_name = loc_arr[0]
                            address = loc_arr[1]
                            city = loc_arr[2]
                    elif len(loc_arr) == 2:
                        if loc_arr[1].strip().lower() == "france":
                            city = loc_arr[0]
                        else:
                            address = loc_arr[0]
                            city = loc_arr[1]

                location_name = location_name.strip()
                address = address.strip()
                city = strip_zip_code(city)

                if address == "":
                    print("Rejecting record: empty address")
                    continue

                ############################################################
                # Localisation sanitizer
                ############################################################
                search_query = f"{address}, {city}, France"
                address_dict = get_address_data(search_query)

                department = address_dict.get("cod_dep", "")
                longitude = address_dict.get("longitude", "")
                latitude = address_dict.get("latitude", "")
                zip_code = address_dict.get("postcode", "")

                if department == "":
                    print("Rejecting record: no result from the national address API")
                    continue

            ################################################################
            # Description
            ################################################################
            description = False

            ################################################################
            # Training?
            ################################################################
            training = False

            ################################################################
            # Is it full?
            ################################################################
            sold_out = False

            ################################################################
            # Is it suited for kids?
            ################################################################
            kids = False

            ################################################################
            # Building final object
            ################################################################
            record = get_record_dict(
                page["id"],
                title,
                event_start_datetime,
                event_end_datetime,
                full_location,
                location_name,
                address,
                city,
                department,
                zip_code,
                latitude,
                longitude,
                online,
                training,
                sold_out,
                kids,
                link,
                link,
                description,
            )

            records.append(record)
            print(f"Successfully scraped {link}\n{json.dumps(record, indent=4)}")
    driver.quit()

    return records
