from utils.driver_factory import DriverFactory
from utils.selenium_utils import SeleniumUtils

import datetime as dt
import os
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.settings import settings

class ExtractDataBase:
    @staticmethod
    def admissoes_ativas():
        driver = DriverFactory.create_browser_driver()
        try:
            SeleniumUtils.login_portal_gpssa(driver)

            time.sleep(5)

            driver.get(settings.URL_ADMISSOES_ATIVAS)

            time.sleep(10)

            DriverFactory.set_download_dir(driver, os.path.join(settings.BASE_DIR, "data_storage"))

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[text()='Exportar']"))
            ).click()

            time.sleep(10)
        finally:
            driver.quit()
