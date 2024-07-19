import csv
import logging
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

BASE_URL = "https://webscraper.io/"
PRODUCT_FIELDS = ["title", "price", "category", "description", "image"]

PRODUCT_OUTPUT_CSV_PATH = "products.csv"


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int
    additional_info: dict


_driver: WebDriver | None = None


def get_driver() -> WebDriver:
    return _driver


def set_driver(new_driver: WebDriver) -> None:
    global _driver
    _driver = new_driver


def product_hdd_block_prices(product_soup: BeautifulSoup) -> dict[str, float]:
    detail_url = urljoin(BASE_URL, product_soup.select_one(".title")["href"])
    driver = get_driver()
    driver.get(detail_url)
    swatches = driver.find_element(By.CLASS_NAME, "swatches")
    buttons = swatches.find_elements(By.TAG_NAME, "button")

    prices = {}

    for button in buttons:
        if not button.get_property("disabled"):
            button.click()
            prices[button.get_property("value")] = float(driver.find_element(
                By.CLASS_NAME, "price"
            ).text.replace("$", ""))

    return prices


def parse_single_product(product_soup: BeautifulSoup) -> Product:
    hdd_prices = product_hdd_block_prices(product_soup)
    return Product(
        title=product_soup.select_one(".title")["title"],
        description=product_soup.select_one(".description").text,
        price=float(product_soup.select_one(".price").text.replace("$", "")),
        rating=int(product_soup.select_one("p[data-rating]")["data-rating"]),
        num_of_reviews=int(
            product_soup.select_one(".review-count").text.split()[0]
        ),
        additional_info={"hdd_prices": hdd_prices}
    )


def get_page_products(url: str, paginate: bool = False) -> [Product]:
    logging.info(f"Start scraping products from {url}")
    driver = get_driver()
    driver.get(url)

    if paginate:
        while True:
            try:
                more_button = driver.find_element(By.CSS_SELECTOR,
                                                  ".btn.btn-lg.btn-block."
                                                  "btn-primary.ecomerce-"
                                                  "items-scroll-more")
                more_button.click()
            except Exception as e:
                logging.info(f"No more pages to load or an error occurred: {e}")
                break

    page_soup = BeautifulSoup(driver.page_source, "html.parser")
    product_soups = page_soup.select(".thumbnail")
    return [parse_single_product(product_soup)
            for product_soup in product_soups]


def write_products_to_csv(products: [Product], filename: str) -> None:
    with open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(PRODUCT_FIELDS)
        for product in products:
            writer.writerow([
                product.title,
                product.description,
                product.price,
                product.rating,
                product.num_of_reviews,
                product.additional_info.get("category", ""),
                product.additional_info.get("image", ""),
            ])


def get_all_products() -> None:
    with webdriver.Chrome() as new_driver:
        set_driver(new_driver)
        pages_info = {
            "home":
                {"path": "test-sites/e-commerce/more/",
                 "paginate": False},
            "computers":
                {"path": "test-sites/e-commerce/more/computers",
                 "paginate": False},
            "laptops":
                {"path": "test-sites/e-commerce/more/computers/laptops",
                 "paginate": True},
            "tablets":
                {"path": "test-sites/e-commerce/more/computers/tablets",
                 "paginate": True},
            "phones":
                {"path": "test-sites/e-commerce/more/phones",
                 "paginate": False},
            "touch":
                {"path": "test-sites/e-commerce/more/phones/touch",
                 "paginate": True}
        }

        for name, info in pages_info.items():
            url = urljoin(BASE_URL, info["path"])
            products = get_page_products(url, paginate=info["paginate"])
            filename = f"{name}.csv"
            write_products_to_csv(products, filename)
        new_driver.quit()


if __name__ == "__main__":
    get_all_products()
