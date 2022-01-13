# -*- coding: utf-8 -*-
import re
import json
from sys import prefix
import time
from urllib import parse
import scrapy
import requests
from hashlib import md5
from copy import deepcopy
from overseaSpider.util.utils import isLinux, filter_text

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'mbeans'
url_prefix = 'https://www.mbeans.com'

currency_json_data = None

def convert_currency(price):
    _from = 'EUR'
    to = 'USD'
    #return "{:.2f}".format(price * currency_json_data[_from] / currency_json_data[to])
    # or 无需转换
    return "{:.2f}".format(price)

def translate_sku_data(raw_sku_data, options_arr):
    sku_item = SkuItem()
    sku_item['current_price'] = convert_currency(float(raw_sku_data['price']))
    sku_item['original_price'] = convert_currency(float(raw_sku_data['compare_at_price'])) if raw_sku_data[
                                                                                                  'compare_at_price'] and float(
        raw_sku_data['compare_at_price']) != 0 else sku_item['current_price']
    sku_item['imgs'] = [raw_sku_data['featured_image']['src']] if raw_sku_data['featured_image'] else []

    sku_attributes_item = SkuAttributesItem()
    for i in range(3):
        optionTitle = raw_sku_data['option' + str(i + 1)]
        if optionTitle and options_arr[i]:
            optionName = options_arr[i]['name'].strip()
            if 'size' in optionName.lower():
                sku_attributes_item['size'] = optionTitle
            elif 'color' in optionName.lower() or 'colour' in optionName.lower():
                sku_attributes_item['colour'] = optionTitle
            else:
                sku_attributes_item['other'] = {optionName: optionTitle}
    sku_item['attributes'] = sku_attributes_item
    return sku_item

def parse_category_by_product_type(product_type, full):
    separators = [' - ', ' > ', '>']
    for separator in separators:
        if separator in product_type:
            arr = product_type.split(separator)
            arr = list(map(lambda cat: cat.replace("/", "／"), arr))
            if full:
                return '/'.join(arr)
            else:
                return arr[-1]
    return product_type.replace("/", "／")

def parse_category_by_tags(tags):
    prefixes = ['type-', '__cat:', 'custom-category-']
    for tag in tags:
        for prefix in prefixes:
            if tag.lower().startswith(prefix):
                return tag[len(prefix):]
    return ''

def item_display_price(skus):
    min_price = float(skus[0]['price'])
    for sku in skus:
        min_price = min(float(sku['price']), min_price)
    return convert_currency(min_price)

def item_original_price(skus):
    max_price = 0.0
    for sku in skus:
        if sku['compare_at_price']:
            max_price = max(float(sku['compare_at_price']), max_price)
    return convert_currency(max_price) if max_price > 0 else item_display_price(skus)

def item_is_available(skus):
    for sku in skus:
        if bool(sku['available']) and float(sku['price']) > 0:
            return True
    return False

def fill_attributes_and_description(shop_item, item_obj):
    body_html = item_obj['body_html']

    if not body_html:
        shop_item["description"] = ''
        return

    body_html = re.sub(r'[\t\n\r\f\v]', ' ', body_html)
    attribute_matches = list(re.finditer(r'(<strong[^><]*>([^><:]+):</strong>([^><]+))<', body_html))
    if len(attribute_matches) > 0:
        shop_item['attributes'] = []
        for match in attribute_matches:
            shop_item['attributes'].append(filter_text(match.group(2).strip() + ": " + match.group(3).strip()))
            body_html = body_html.replace(match.group(1), "")
    shop_item["description"] = filter_text(body_html)


class ShopSpider(scrapy.Spider):
    name = website
    # allowed_domains = [domain_name]
    # start_urls = ['http://https://www.mbeans.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = True
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(ShopSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "阿斌")

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
         # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):
        yield scrapy.Request(
            url=url_prefix + '/services/javascripts/currencies.js',
            callback=self.get_currency_rates,
            )  # 获取汇率转换表

    def get_currency_rates(self, response):
        currency_json_str = re.search(r'rates:\s*(\{.*?\})', response.text).group(1)
        global currency_json_data
        currency_json_data = json.loads(currency_json_str)
        yield scrapy.Request(
            url=url_prefix + '/products.json?page=1&limit=250',
            callback=self.parse,
            cookies={
            # 'cart_currency': 'USD'
            }
        )  # limit 最大为 250，超过无效

    def parse(self, response):
        json_data = json.loads(response.text)
        items_list = list(json_data['products'])

        if items_list:
            coms = list(parse.urlparse(response.url))
            params = parse.parse_qs(coms[4])
            params['page'] = [int(params['page'][0]) + 1]
            coms[4] = parse.urlencode(params, True)
            next_page_url = parse.urlunparse(coms)

            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
                cookies={
                    # 'cart_currency': 'USD'
                }
            )

            for item_obj in items_list:
                if not item_is_available(item_obj['variants']):
                    continue

                if len(list(item_obj['images'])) == 0:
                    continue

                item = ShopItem()

                item["url"] = url_prefix + '/products/' + str(item_obj['handle'])
                item["current_price"] = item_display_price(item_obj['variants'])
                item["original_price"] = item_original_price(item_obj['variants'])
                item["brand"] = item_obj['vendor']
                item["name"] = item_obj['title']

                # item["cat"] = parse_category_by_tags(item_obj['tags'])
                item["cat"] = parse_category_by_product_type(item_obj['product_type'], False)
                # item["detail_cat"] = parse_category_by_tags(item_obj['tags'])
                item["detail_cat"] = parse_category_by_product_type(item_obj['product_type'], True)
                fill_attributes_and_description(item, item_obj)
                item["source"] = website
                item["images"] = list(map(lambda obj: obj['src'], item_obj['images']))
                item["sku_list"] = list(map(lambda sku: translate_sku_data(sku, item_obj['options']), item_obj['variants']))
                item["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]

                status_list = list()
                status_list.append(item["url"])
                status_list.append(item["original_price"])
                status_list.append(item["current_price"])
                status_list = [i for i in status_list if i]
                status = "-".join(status_list)
                item["id"] = md5(status.encode("utf8")).hexdigest()

                item["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                item["created"] = int(time.time())
                item["updated"] = int(time.time())
                item['is_deleted'] = 0


                # 如果详情页没有breadcrumb或为Home + name则全部注释
                # 如果详情页有breadcrumb，取消下面多行注释，并自行抓取breadcrumb_list
                # item["cat"] = ""
                # item["detail_cat"] = ""
                # if not item["cat"] or not item["detail_cat"]:
                #     Breadcrumb_list = response.xpath("//nav[contains(@class, 'breadcrumb')]//a/span/text()").getall()
                #     Breadcrumb_list.append(item["name"])
                    # if not Breadcrumb_list:
                    #     Breadcrumb_list = ["Home", item["name"]]
                    # item["cat"] = Breadcrumb_list[-1]
                    # item["detail_cat"] = "/".join(Breadcrumb_list)

                # mbeans


                # print(item)
                yield item

                #yield scrapy.Request(
                    #url=item["url"],
                    #callback=self.parse_detail,
                    #cookies={
                    #    # 'cart_currency': 'USD'
                    #},
                    #meta={"item": deepcopy(item)}
                #)

    #def parse_detail(self, response):
    #     item = response.meta.get("item")
    #     response.xpath("").get()
    #
    #     yield item






