import logging
from bs4 import BeautifulSoup
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from requests_html import HTMLSession
from selenium.webdriver.chrome.options import Options
import os
import io
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage
import uuid


def replaceTextBetween(originalText, replacementText):
    # 😤this is the no regex zone🙅‍♀️
    # all my homies hate regex 👎💥
    delimiterA = "width="
    delimiterB = ",format"

    # eg https://img.cdn4dd.com/cdn-cgi/image/fit=contain,width=1920,format=auto,quality=50/https://cdn.doordash.com/media/photos/81b5393f-36d6-4c84-a9de-ed7afcf8e301-retina-large.jpg 1920w
    # looking for this, change width=1920 to width=400
    leadingText = originalText.split(delimiterA)[0]
    trailingText = originalText.split(delimiterB)[1]
    newString = leadingText + delimiterA + \
        replacementText + delimiterB + trailingText
    return newString


def cleanPrice(price):
    cleanPrice = ""
    allowedChars = list("1234567890,.")
    for char in price:
        if char in allowedChars:
            cleanPrice += char


def handleImage(doordashImgUrl, ):
    # this is SO STUPID
    # first get compressed version of image
    id = uuid.uuid4()

    reducedImgSize = "400"
    smallerDoordashImgUrl = replaceTextBetween(doordashImgUrl, reducedImgSize)
    response = requests.get(smallerDoordashImgUrl)

    # Upload it to firebase
    bucket = storage.bucket("menu-buddy-9c09c.appspot.com")
    blob = bucket.blob(f'images/{id}.jpg')
    # should i make separate buckets for each restaurant
    blob.upload_from_string(response.content, content_type='image/jpeg')

    # then get and return its new image url
    blob.make_public()
    return blob.public_url


def scrape_from_url(url):

    cred = credentials.Certificate(
        './menu-buddy-9c09c-firebase-adminsdk-x7p8i-37b112465c.json')
    app = firebase_admin.initialize_app(cred)
    # comment me out for home use
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    browser = webdriver.Chrome(
        executable_path=os.environ.get("CHROMEDRIVER_PATH"),
        options=chrome_options
    )
    # Uncomment me out:
    # browser = webdriver.Firefox()

    session = HTMLSession()
    page = browser.get(url)
    wait(browser, 10).until(
        lambda browser: browser.find_element_by_tag_name("h1"))

    soup = BeautifulSoup(browser.page_source, 'lxml')
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
                dish["price"] = cleanPrice(t[3].text)
            except:
                pass
            try:
                img = button.findAll("img")
                if len(img) > 0:
                    dish["imageUrl"] = handleImage(img[0]['srcset'].split()[0])
            except:
                pass
        if catName not in categories:
            categories[catName] = {"name": catName,
                                   "description": catDesc, "dishes": [dish]}
        else:
            newDishes = categories[catName]["dishes"]
            newDishes.append(dish)
            categories[catName]["dishes"] = newDishes
    if "uncategorized" in categories:
        del categories["uncategorized"]
    if "Popular Items" in categories:
        # removing this because it's autogenerated
        del categories["Popular Items"]
    browser.close()
    return(categories)


# uncomment me
# scrape_from_url(
#     "https://www.doordash.com/store/red-robin-gourmet-burgers-bc-victoria-954678")


# # Comment me out
app = Flask(__name__)
CORS(app)


@app.route("/<urlExtension>", methods=["GET"])
def render(urlExtension):
    url = "https://www.doordash.com/store/" + urlExtension
    categories = scrape_from_url(url)
    return jsonify(categories), 201
