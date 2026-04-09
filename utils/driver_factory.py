import os

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service


class DriverFactory:
    @staticmethod
    def create_edge_driver(worker_id=None):
        if os.name == "nt":
            default_driver_path = r"C:\WebDrivers\msedgedriver.exe"
        else:
            default_driver_path = "/usr/local/bin/msedgedriver"

        driver_path = os.getenv("EDGE_DRIVER_PATH", default_driver_path)

        options = Options()
        options.use_chromium = True

        # ESSENCIAL PRA VPS / Docker
        headless = os.getenv("HEADLESS", "true").strip().lower() in {"1", "true", "yes", "on"}
        if headless:
            options.add_argument("--headless=new")

        # Performance / estabilidade
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Reducao de consumo
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        # Nao carregar imagens (economia)
        prefs = {
            "profile.managed_default_content_settings.images": 2
        }
        options.add_experimental_option("prefs", prefs)

        # Perfil por worker (mantem login)
        if worker_id is not None:
            options.add_argument(f"--user-data-dir=/tmp/edge-profile-{worker_id}")

        # Tamanho fixo (menos custo de renderizacao)
        options.add_argument("--window-size=1920,1080")

        if not driver_path or not os.path.exists(driver_path):
            raise FileNotFoundError(
                f"WebDriver nao encontrado em '{driver_path}'. Defina EDGE_DRIVER_PATH corretamente."
            )

        service = Service(executable_path=driver_path)
        driver = webdriver.Edge(service=service, options=options)

        return driver
