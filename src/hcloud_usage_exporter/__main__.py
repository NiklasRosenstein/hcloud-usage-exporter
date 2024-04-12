import os
from argparse import ArgumentParser
import logging
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from prometheus_client import Gauge, Counter, start_http_server
from pyotp import TOTP
import time

logger = logging.getLogger(__name__)


def create_driver() -> WebDriver:
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("user-data-dir=.cookies")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-dev-shm-using")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")  # Required to prevent "DevToolsActivePort file doesn't exist"
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True, )
    driver.implicitly_wait(10)
    return driver


class HCloudClient:

    def __init__(self, driver: WebDriver) -> None:
        self._driver = driver

    def login(self, username: str, password: str, totp: str | None) -> None:
        logger.info("Logging into HCloud Console as %s ...", username)
        self._driver.get("https://console.hetzner.cloud")

        username_input = self._driver.find_element(by=By.ID, value="_username")
        password_input = self._driver.find_element(by=By.ID, value="_password")
        login_button = self._driver.find_element(by=By.ID, value="submit-login")

        username_input.send_keys(username)
        password_input.send_keys(password)
        login_button.click()

        if totp is not None:
            totp_input = self._driver.find_element(by=By.ID, value="input-verify-code")
            totp_input.send_keys(totp)

            verify_button = self._driver.find_element(by=By.ID, value="btn-submit")
            verify_button.click()

        # TODO: Check if TOTP is asked for but we don't have it

    def get_usage(self) -> list[tuple[str, float]]:
        logger.info("Fetching usage summary ...")
        self._driver.get("https://console.hetzner.cloud/usage")

        # Wait for the table to load, otherwise we find the placeholder table and it gets shortly replaced after.
        import time; time.sleep(5)

        result = []
        table = self._driver.find_element(by=By.CLASS_NAME, value="usage-table")
        tbody = table.find_element(by=By.TAG_NAME, value="tbody")
        for row in tbody.find_elements(by=By.TAG_NAME, value="tr"):
            project_name = row.find_element(by=By.CLASS_NAME, value="usage-table__project-name").text
            usage_total = row.find_element(by=By.CLASS_NAME, value="usage-table__col-total").text
            usage_total = float(usage_total.replace("€", ""))
            result.append((project_name, usage_total))

        return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = ArgumentParser()
    parser.add_argument("--username", type=str, default=os.getenv("HCLOUD_USERNAME"))
    parser.add_argument("--password", type=str, default=os.getenv("HCLOUD_PASSWORD"))
    parser.add_argument("--totp-secret", type=str, default=os.getenv("HCLOUD_TOTP_SECRET"))
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--metrics-port", type=int, default=3000)
    args = parser.parse_args()

    logger.info("Arguments: %s", args)
    if not args.username:
        parser.error("Please provide a username via --username or HCLOUD_USERNAME")
    if not args.password:
        parser.error("Please provide a password via --password or HCLOUD_PASSWORD")

    start_http_server(args.metrics_port)

    login_counter = Counter("hcloud_usage_logins", "Total logins")
    fetch_counter = Counter("hcloud_usage_fetches", "Total fetches")
    error_counter = Counter(f"hcloud_usage_errors", f"Total errors while fetching usage")
    usage_gauge = Gauge(f"hcloud_usage_total_eur", "Total usage in EUR for project {project_name}", ["project_name"])

    totp = TOTP(args.totp_secret).now() if args.totp_secret else None
    client = HCloudClient(create_driver())
    client.login(args.username, args.password, totp)
    login_counter.inc()

    last_update = None
    while True:
        try:
            usage = client.get_usage()
            fetch_counter.inc()
            logger.info("Usage summary: %s", usage)
            for project_name, total in usage:
                usage_gauge.labels(project_name=project_name).set(total)
        except Exception:
            logger.exception(f"Error while fetching usage")
            error_counter.inc()

            # Re-login, in case the session is expired
            totp = TOTP(args.totp_secret).now() if args.totp_secret else None
            client.login(args.username, args.password, totp)
            login_counter.inc()

        # Wait for the next interval
        current_time = time.perf_counter()
        if last_update is not None:
            time.sleep(max(0, args.interval - (current_time - last_update)))
        else:
            time.sleep(args.interval)
        last_update = current_time


if __name__ == '__main__':
    main()
