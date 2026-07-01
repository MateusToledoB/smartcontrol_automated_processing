import os
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

class DriverFactory:
    @staticmethod
    def create_browser_driver():
        options = Options()
        options.page_load_strategy = "eager"

        options.binary_location = (
            os.getenv("CHROME_HEADLESS_SHELL_PATH")
            or shutil.which("chrome-headless-shell")
            or shutil.which("chromium")
            or shutil.which("google-chrome")
        )

        # Mantem o consumo de GPU baixo mesmo com varios drivers abertos em paralelo
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-gpu-compositing")
        options.add_argument("--use-gl=disabled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        # Reduz CPU/RAM por instancia para escalar varios bots simultaneos
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--no-first-run")
        options.add_argument("--mute-audio")
        options.add_argument("--disable-default-apps")

        prefs = {
            "profile.managed_default_content_settings.images": 2
        }
        options.add_experimental_option("prefs", prefs)

        # Nao definir --user-data-dir: o chromedriver ja cria um profile temporario
        # isolado por sessao automaticamente, o que garante isolamento entre os bots
        # concorrentes. Passar um --user-data-dir explicito quebra a criacao de sessao
        # do chrome-headless-shell (SessionNotCreatedException: "unable to discover
        # open pages"), confirmado em teste local com chromedriver 150.
        options.add_argument("--window-size=1920,1080")

        chromedriver_path = os.getenv("CHROMEDRIVER_PATH") or shutil.which("chromedriver")
        service = Service(executable_path=chromedriver_path) if chromedriver_path else Service()
        driver = webdriver.Chrome(service=service, options=options)

        return driver

    @staticmethod
    def set_download_dir(driver, download_path: str):
        os.makedirs(download_path, exist_ok=True)
        driver.execute_cdp_cmd(
            "Browser.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_path},
        )
