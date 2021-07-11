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


def cleanPrice(price):
    numbers = list('1234567890$.,')
    cleanPrice = ""
    for char in price:
        if char in numbers:
            cleanPrice += char
    return cleanPrice


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


def handleImage(doordashImgUrl, ):
    # this is SO STUPID
    # first get compressed version of image
    id = uuid.uuid4()

    reducedImgSize = "400"
    print("handling...")
    smallerDoordashImgUrl = replaceTextBetween(doordashImgUrl, reducedImgSize)
    response = requests.get(smallerDoordashImgUrl)
    print("Response gotten")
    # Upload it to firebase
    bucket = storage.bucket("menu-buddy-9c09c.appspot.com")
    blob = bucket.blob(f'images/{id}.jpg')
    print("Blob gotten")
    # should i make separate buckets for each restaurant
    blob.upload_from_string(response.content, content_type='image/jpeg')

    # then get and return its new image url
    blob.make_public()
    return blob.public_url


def scrape_from_url(url):

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
    # # Uncomment me out:
    # browser = webdriver.Firefox()
    session = HTMLSession()
    page = browser.get(url)
    wait(browser, 10).until(
        lambda browser: browser.find_element_by_tag_name("h1"))

    soup = BeautifulSoup(browser.page_source, 'lxml')
    categories = {"uncategorized": {
        "name": "uncategorized", "description": "", "dishes": []}}
    menuItems = soup.find_all("div", {"data-anchor-id": "MenuItem"})
    index = 0
    for menuItem in menuItems:
        dish = {
            "name": "",
            "description": "",
            "price": "",
            "categoryName": "",
        }

        cat = menuItem.parent.parent
        if cat is not None:
            catName = ""
            catDesc = ""
            try:
                if cat.find("h2"):
                    catName = cat.find("h2").text

                else:
                    catName = menuItem.parent.parent.parent.find("h2").text

                dish["categoryName"] = catName
            except:
                pass
            try:
                if cat.find("h3"):
                    catDesc = cat.find(
                        "h3").text
                else:
                    catDesc = menuItem.parent.parent.parent.find("h3").text
                dish["categoryDescription"] = catName
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
            # try:
            img = button.findAll("img")
            print(img)
            if len(img) > 0:
                print(handleImage(img[0]['srcset'].split()[0]))
                dish["imageUrl"] = handleImage(img[0]['srcset'].split()[0])
            # except:
            #     pass
        if catName not in categories:

            categories[catName] = {"name": catName,
                                   "description": catDesc, "dishes": [dish], "index": index}
            index += 1
        else:
            newDishes = categories[catName]["dishes"]
            newDishes.append(dish)
            categories[catName]["dishes"] = newDishes
    try:
        del categories["uncategorized"]
        # removing this because it's autogenerated
        del categories["Popular Items"]
    except:
        pass
    browser.close()
    print(categories)
    return(categories)


# uncomment me
# scrape_from_url(
#     "https://www.doordash.com/store/cactus-club-cafe-victoria-894725")


# Comment me out
cred = credentials.Certificate(
    './menu-buddy-9c09c-firebase-adminsdk-x7p8i-37b112465c.json')
app = firebase_admin.initialize_app(cred)
app = Flask(__name__)
CORS(app)


@app.route("/<urlExtension>", methods=["GET"])
def render(urlExtension):
    url = "https://www.doordash.com/store/" + urlExtension
    categories = scrape_from_url(url)
    return jsonify(categories), 201
