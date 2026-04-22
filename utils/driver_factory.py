import os
import shutil

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager


class DriverFactory:
    # @staticmethod
    # def create_edge_driver(worker_id=None):
    #     options = Options()
    #     options.use_chromium = True

    #     options.binary_location = (
    #         os.getenv("EDGE_BINARY_PATH")
    #         or shutil.which("microsoft-edge")
    #         or shutil.which("msedge")
    #     )

    #     headless = os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"}
    #     if headless:
    #         options.add_argument("--headless=new")

    #     options.add_argument("--disable-gpu")
    #     options.add_argument("--no-sandbox")
    #     options.add_argument("--disable-dev-shm-usage")

    #     options.add_argument("--disable-extensions")
    #     options.add_argument("--disable-infobars")
    #     options.add_argument("--disable-notifications")
    #     options.add_argument("--disable-popup-blocking")

    #     prefs = {
    #         "profile.managed_default_content_settings.images": 2
    #     }
    #     options.add_experimental_option("prefs", prefs)

    #     if worker_id:
    #         options.add_argument(f"--user-data-dir=/tmp/edge-profile-{worker_id}")

    #     options.add_argument("--window-size=1920,1080")

    #     driver = webdriver.Edge(options=options)

    #     return driver

    @staticmethod
    def create_edge_driver(worker_id=None):
        # Caminho para o msedgedriver.exe
        driver_path = r"C:\WebDrivers\msedgedriver.exe"

        # Configurar o EdgeOptions corretamente
        options = Options()
        options.use_chromium = True  # Isso é OBRIGATÓRIO!
        #options.add_argument('--headless=new')     # Modo headless moderno
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument("--window-size=1920,1080")

        # Cria o serviço com o caminho correto
        service = Service(executable_path=driver_path)

        # Inicia o navegador
        driver = webdriver.Edge(service=service, options=options)
        return driver