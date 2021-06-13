import logging
from bs4 import BeautifulSoup
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from requests_html import HTMLSession
from selenium.webdriver.chrome.options import Options
import os
from flask import Flask, render_template, jsonify
from flask_cors import CORS


def bruteForceCleanTextLol(text):
    try:
        text1 = text.string.lower()
    except:
        text1 = text.lower()
    text = " ".join(text.split(","))
    text = " ".join(text.split('.'))
    text = " ".join(text.split('('))
    text = " ".join(text.split(')'))
    text = " ".join(text.split('"'))
    text = " ".join(text.split('-'))
    text = " ".join(text.split(':')).lower()

# def veganCatcher(text):
#     text = bruteForceCleanTextLol(text)
#     vegan = re.search(
#         r'\bvegan\b', text)
#     if vegan:
#         return True


def scrape_from_url(url):
    print("scraping...")
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    browser = webdriver.Chrome(
        executable_path=os.environ.get("CHROMEDRIVER_PATH"),
        options=chrome_options
    )

    session = HTMLSession()
    page = browser.get(url)
    wait(browser, 10).until(
        lambda browser: browser.find_element_by_tag_name("h1"))

    soup = BeautifulSoup(browser.page_source, 'lxml')
    return soup.find("h1").text
    categories = {"uncategorized": {
        "name": "uncategorized", "description": "", "dishes": []}}
    menuItems = soup.find_all("div", {"data-anchor-id": "MenuItem"})
    for menuItem in menuItems:
        dish = {
            "name": "",
            "description": "",
            "price": "",
            "categoryName": "",
        }
        cat = menuItem.parent.previous_sibling

        if cat is not None:
            try:
                catName = menuItem.parent.previous_sibling.find("h2").text
                dish["categoryName"] = catName
            except:
                pass
            try:
                catDesc = menuItem.parent.previous_sibling.find("h3").text
            except:
                pass
        else:
            catName = "uncategorized"
        buttons = menuItem.findAll("button")
        for button in buttons:

            t = button.findAll("span")
            try:
                dish["name"] = t[1].text
            except:
                pass
            try:
                dish["description"] = t[2].text
            except:
                pass
            try:
                dish["price"] = t[3].text
            except:
                pass
        if catName not in categories:
            categories[catName] = {"name": catName,
                                   "description": catDesc, "dishes": [dish]}
        else:
            newDishes = categories[catName]["dishes"]
            newDishes.append(dish)
            categories[catName]["dishes"] = newDishes
    del categories["uncategorized"]
    return(categories)


app = Flask(__name__)
CORS(app)
# if __name__ == "__main__":


@app.route("/<string:url>", methods=["GET"])
def render(url):
    categories = scrape_from_url(url)
    print(categories)
    return jsonify(categories), 201

    # return (render_template("index.html", title=title))
