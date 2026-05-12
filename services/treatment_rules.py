import datetime as dt
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.settings import settings

class TreatmentRules:
    @staticmethod
    def wait_for_element(driver, by, value, timeout=10):
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

    @staticmethod
    def wait_for_elements(driver, by, value, timeout=10):
        return WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((by, value)))

    @staticmethod
    def extract_date_from_text(text):
        date_pattern = r'(\d{2}/\d{2}/\d{4})'
        match = re.search(date_pattern, text)
        if match:
            date_str = match.group(1)
            try:
                return dt.datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                return None
        return None