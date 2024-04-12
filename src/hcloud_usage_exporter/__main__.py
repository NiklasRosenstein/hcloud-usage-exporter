import os
from argparse import ArgumentParser
import logging
from pathlib import Path
from typing import ClassVar, Literal
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from prometheus_client import Enum, Gauge, Counter, Summary, start_http_server
from pyotp import TOTP
import time

logger = logging.getLogger(__name__)

PAGE_HISTORY_DIR = "/var/lib/hcloud-usage-exporter/error-histoy"


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
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
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
        time.sleep(5)

        result = []
        table = self._driver.find_element(by=By.CLASS_NAME, value="usage-table")
        tbody = table.find_element(by=By.TAG_NAME, value="tbody")
        for row in tbody.find_elements(by=By.TAG_NAME, value="tr"):
            project_name = row.find_element(by=By.CLASS_NAME, value="usage-table__project-name").text
            usage_total = row.find_element(by=By.CLASS_NAME, value="usage-table__col-total").text
            usage_total = float(usage_total.replace("€", ""))
            result.append((project_name, usage_total))

        return result


class PageSnapshotter:
    def __init__(self, path: Path, max_history: int) -> None:
        self._path = path
        self._max_history = max_history

    def capture(self, driver: WebDriver) -> Path:
        self._path.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        path = self._path / f"{timestamp}.png"
        driver.save_screenshot(str(path))

        # Cleanup old snapshots
        snapshots = sorted(self._path.glob("*.png"))
        for snapshot in snapshots[: -self._max_history]:
            snapshot.unlink()

        return path


class Timer:
    """Helper class for timing."""

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self._start

    def sleep_delta(self, seconds: float) -> None:
        time.sleep(max(0, seconds - self.elapsed()))
        self._start = time.perf_counter()


class Metrics:
    state: ClassVar = Enum(
        "hcloud_usage_exporter_state", "Current state of the exporter", states=["pending", "healthy", "error"]
    )
    login_count: ClassVar = Counter("hcloud_usage_exporter_logins", "Total number of logins")
    fetch_count: ClassVar = Counter("hcloud_usage_exporter_fetches", "Total number of fetches")
    error_count: ClassVar = Counter("hcloud_usage_exporter_errors", "Total number of errors")
    project_cost_eur: ClassVar = Gauge(
        "hcloud_usage_exporter_project_cost_eur", "Total cost in EUR for projects", ["project_name"]
    )
    loop_duration_seconds: ClassVar = Summary(
        "hcloud_usage_exporter_loop_duration_seconds", "Duration of a single main loop in seconds"
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = ArgumentParser()
    parser.add_argument("--username", type=str, default=os.getenv("HCLOUD_USERNAME"))
    parser.add_argument("--password", type=str, default=os.getenv("HCLOUD_PASSWORD"))
    parser.add_argument("--totp-secret", type=str, default=os.getenv("HCLOUD_TOTP_SECRET"))
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--metrics-port", type=int, default=3000)
    args = parser.parse_args()

    if not args.username:
        parser.error("Please provide a username via --username or HCLOUD_USERNAME")
    if not args.password:
        parser.error("Please provide a password via --password or HCLOUD_PASSWORD")

    start_http_server(args.metrics_port)

    client = HCloudClient(create_driver())
    state: Literal["pending", "healthy", "error"] = "pending"
    timer = Timer()
    snapshotter = PageSnapshotter(Path(PAGE_HISTORY_DIR), max_history=10)

    Metrics.state.state(state)

    while True:
        # Ensure that we're logged in.
        match state:
            case "pending" | "error":
                logger.info("Currently in state %s, trying to login ...", state)
                totp = TOTP(args.totp_secret).now() if args.totp_secret else None
                try:
                    client.login(args.username, args.password, totp)
                except Exception:
                    state = "error"
                    Metrics.error_count.inc()
                    path = snapshotter.capture(client._driver)
                    logger.exception("Error while logging in, captured snapshot: %s", path)
                else:
                    Metrics.login_count.inc()
                    state = "healthy"

        Metrics.state.state(state)
        match state:
            case "error":
                Metrics.project_cost_eur.clear()
            case "healthy":
                logger.info("Fetching project cost ...")
                try:
                    usage = client.get_usage()
                except Exception:
                    state = "error"
                    Metrics.error_count.inc()
                    path = snapshotter.capture(client._driver)
                    logger.exception("Error while fetching usage, captured snapshot: %s", path)
                else:
                    Metrics.fetch_count.inc()
                    for project_name, total in usage:
                        Metrics.project_cost_eur.labels(project_name=project_name).set(total)

        Metrics.state.state(state)
        Metrics.loop_duration_seconds.observe(timer.elapsed())
        timer.sleep_delta(args.interval)


if __name__ == "__main__":
    main()
