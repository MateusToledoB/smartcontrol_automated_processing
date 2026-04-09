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

        # Detecta binário do Edge no container
        options.binary_location = (
            os.getenv("EDGE_BINARY_PATH")
            or shutil.which("microsoft-edge")
            or shutil.which("msedge")
        )

        # Headless (controlado por env)
        headless = os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"}
        if headless:
            options.add_argument("--headless=new")

        # 🔥 Estabilidade em container
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # 🔻 Redução de consumo
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-popup-blocking")

        # 🔥 Evita crashes silenciosos
        options.add_argument("--remote-debugging-port=9222")

        # 🔥 Otimização extra
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--metrics-recording-only")

        # 🔥 Não carregar imagens (economia real)
        prefs = {
            "profile.managed_default_content_settings.images": 2
        }
        options.add_experimental_option("prefs", prefs)

        # 🔥 Perfil isolado por worker (mantém login)
        if worker_id is not None:
            options.add_argument(f"--user-data-dir=/tmp/edge-profile-{worker_id}")

        # Tamanho fixo
        options.add_argument("--window-size=1920,1080")

        # 🔥 CACHE DO DRIVER (EVITA DOWNLOAD TODA HORA)
        cache_manager = DriverCacheManager(valid_range=7)
        edge_driver_path = EdgeChromiumDriverManager(
            cache_manager=cache_manager
        ).install()

        service = Service(edge_driver_path)

        return webdriver.Edge(service=service, options=options)