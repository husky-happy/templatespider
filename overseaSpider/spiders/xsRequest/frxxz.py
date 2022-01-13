import requests
import json
from scrapy.selector import Selector
website_url = 'https://www.23usb.com/'
url = 'https://www.23usb.com/xs_77/'

# def parse()
response = requests.get(url)
new_response = Selector(response)