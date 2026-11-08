import os
import unittest
from pathlib import Path

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from store.models import Product

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.chrome.service import Service
except ImportError:  # Keep the regular Django test suite usable without dev extras.
    webdriver = None
    By = EC = WebDriverWait = None
    Service = None


@unittest.skipUnless(
    webdriver is not None and os.environ.get("RUN_BROWSER_TESTS") == "1",
    "Install requirements-dev.txt and set RUN_BROWSER_TESTS=1 to run Selenium tests.",
)
class StoreBrowserSmokeTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1440,1000")
        if os.environ.get("CHROME_BIN"):
            options.binary_location = os.environ["CHROME_BIN"]
        driver_path = os.environ.get("CHROMEDRIVER")
        service = Service(executable_path=driver_path) if driver_path else None
        cls.browser = webdriver.Chrome(service=service, options=options)
        cls.browser.set_page_load_timeout(30)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "browser"):
            cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        Product.objects.create(
            name="عطر المتصفح",
            name_en="Browser Test Perfume",
            description="عطر للاختبار",
            description_en="A browser test product",
            price="99.00",
            stock=2,
        )

    def test_customer_can_add_a_fragrance_and_view_the_cart(self):
        self.browser.get(f"{self.live_server_url}/en/")
        add_button = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".cart-add-form button[type='submit']"))
        )
        add_button.click()

        WebDriverWait(self.browser, 10).until(
            lambda browser: browser.find_element(By.CSS_SELECTOR, ".cart-count").text.strip() == "1"
        )
        self.browser.get(f"{self.live_server_url}/en/cart/")
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".cart-item"))
        )
        self.assertIn("Browser Test Perfume", self.browser.find_element(By.CSS_SELECTOR, ".cart-item").text)
        artifact_dir = os.environ.get("TEST_ARTIFACT_DIR")
        if artifact_dir:
            Path(artifact_dir).mkdir(parents=True, exist_ok=True)
            self.browser.save_screenshot(str(Path(artifact_dir) / "perfume-cart-smoke.png"))
