import os
import shutil

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager


class DriverFactory:
    @staticmethod
    def create_edge_driver(worker_id=None):
        options = Options()
        options.use_chromium = True

        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        if worker_id is not None:
            options.add_argument(f"--user-data-dir=/tmp/edge-profile-{worker_id}")

        # 🔥 usa driver local (SEM download)
        service = Service("/usr/local/bin/msedgedriver")