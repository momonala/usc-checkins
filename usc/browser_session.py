import logging
import platform
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FireFoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@contextmanager
def virtual_display_if_needed():
    if running_on_rpi():
        from pyvirtualdisplay import Display

        with Display(visible=0):
            logger.info("Launching virtual display...")
            yield
    else:
        logger.info("Not using virtual display...")
        yield


@contextmanager
def browser_session():
    if running_on_rpi():
        webdriver_service = FireFoxService(GeckoDriverManager(os_type="linux-aarch64").install())
        webdriver_options = webdriver.FirefoxOptions()
        webdriver_options.add_argument('--headless=new')
        webdriver_options.page_load_strategy = 'eager'
        browser = webdriver.Firefox(service=webdriver_service, options=webdriver_options)
        logger.info("Using Firefox webdriver.")
    else:
        webdriver_service = ChromeService(executable_path=ChromeDriverManager().install())
        webdriver_options = webdriver.ChromeOptions()
        webdriver_options.add_argument('--headless=new')
        webdriver_options.page_load_strategy = 'eager'
        browser = webdriver.Chrome(service=webdriver_service, options=webdriver_options)
        logger.info("Using Chrome webdriver.")
    browser.implicitly_wait(10)
    yield browser
    browser.quit()


def running_on_rpi() -> bool:
    return platform.machine() == "aarch64"
