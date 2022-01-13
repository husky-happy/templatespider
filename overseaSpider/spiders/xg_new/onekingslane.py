# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'onekingslane'


class OnekingslaneSpider(scrapy.Spider):
    name = website

    # allowed_domains = ['onekingslane.com']
    # start_urls = ['http://onekingslane.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/dashu/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(OnekingslaneSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "十树")

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
            # 'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):
        url = "https://www.onekingslane.com/"
        yield scrapy.Request(
            url=url,
        )
        # yield scrapy.Request(
        #     url="https://www.onekingslane.com/p/2047743-kelly-wingback-bed-talc-linen.do?sortby=bestSellersAscend&refType=&from=fn&catnav=119587",
        #     callback=self.parse_detail
        # )

    def parse(self, response):
        nav_list = response.xpath("//a[@class='ml-category-nav-name']")
        url_list = list()
        for nav in nav_list:
            if nav.xpath("./text()").get().strip() == "Shop All":
                url = nav.xpath("./@href").get()
                if "sale-all" not in url:
                    url_list.append(url)
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print("列表页:" + url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//div[@class='ml-grid-view-item']//div[@class='ml-thumb-image']/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print("详情页:" + url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )

        next_page_url = response.xpath("//a[@class='ml-paging-next ml-icon-lib ml-icon-next']/@href").get()
        if next_page_url:
            next_page_url = response.urljoin(next_page_url)
            # print("下一页:" + next_page_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        items["source"] = website
        print(1111111)
        data_str = re.findall("var oGoogleAnalyticsJSON = (.*?);", response.text)[0]
        data = json.loads(data_str)
        product = data['enhancedEcommerce']['measuredData'][0]['products'][0]
        items["brand"] = product['brand']
        items["name"] = product['name']
        items["cat"] = product['category'].split("/")[-1]
        items["detail_cat"] = product['category']

        original_price = response.xpath(
            "//div[@class='ml-product-alt-detail-info']//span[contains(@class,'ml-item-price-was')]/text()").get()
        current_price = response.xpath(
            "//div[@class='ml-product-alt-detail-info']//span[contains(@class,'ml-item-price')]/text()").get()
        items["original_price"] = "" + str(original_price) if original_price else "" + str(current_price)
        items["current_price"] = "" + str(current_price) if current_price else "" + str(original_price)
        if "-" in items["original_price"]:
            items["original_price"] = items["original_price"].split("-")[0].strip()
        if "-" in items["current_price"]:
            items["current_price"] = items["current_price"].split("-")[0].strip()

        attributes = list()
        info_columns = response.xpath("//div[@class='ml-info-content-column']")
        if info_columns and len(info_columns) != 0:
            for column in info_columns:
                attr = column.xpath("string(.)").get().strip().replace("\n", "").replace("\t", "").replace("\r", "")
                attr = re.sub(' +', ' ', attr)
                attributes.append(attr)
        items["attributes"] = attributes
        # items["about"] = response.xpath("").get()
        items["description"] = response.xpath("//div[@id='whyWeLoveSection']/p/text()").get()
        # items["care"] = response.xpath("").get()
        # items["sales"] = response.xpath("").get()
        images_list = list()
        images_data = response.xpath("//div[@id='detailViewContainer']/div/a/img/@src").getall()
        if not images_data:
            images_data = response.xpath("//div[@class='detailImage  img-responsive']/a/@href").getall()
        for i in images_data:
            index = i.find("Product_")
            images_list.append(i[:index]+"Product_Zoom-Product")

        items["images"] = images_list

        sku_list = list()
        prices = response.xpath("//input[@id='tealiumJsonObject']/@value").get()
        prices = json.loads(prices)
        price_d = dict()
        for i in range(0, len(prices['product_okl_price'])):
            price_d["$" + prices['product_okl_price'][i]] = "$" + prices['product_original_price'][i]

        options = re.findall("MarketLive.P2P.buildEnhancedDependentOptionMenuObjects\((.*?)\);", response.text)[0]
        options = json.loads(options)
        for key in options["aOptionSkus"]:
            sku = options["aOptionSkus"][key]
            if len(sku["skuOptions"]) == 0:
                continue
            sku_item = SkuItem()
            sku_item["current_price"] = sku["skuPrice"].replace(",", "")
            sku_item["original_price"] = price_d[sku_item["current_price"]]
            sku_item["inventory"] = 10
            attributes = SkuAttributesItem()
            other = dict()
            for key1 in sku["skuOptions"]:
                current_option_pk = sku["skuOptions"][key1]["iOptionPk"]
                option_type = options["aOptionTypes"][key1]
                name = option_type["sOptionTypeName"]
                desc = ""
                for key2 in option_type["options"]:
                    value = option_type["options"][key2]
                    if value["iOptionPk"] == current_option_pk:
                        desc = value["sOptionName"]
                if name == "Size":
                    attributes["size"] = desc
                elif name == "Color":
                    attributes["colour"] = desc
                else:
                    other[name] = desc
            if len(other) != 0:
                attributes["other"] = other
            sku_item["attributes"] = attributes
            sku_list.append(sku_item)

        items["sku_list"] = sku_list
        items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]
        status_list = list()
        status_list.append(items["url"])
        status_list.append(items["original_price"])
        status_list.append(items["current_price"])
        status_list = [i for i in status_list if i]
        status = "-".join(status_list)
        items["id"] = md5(status.encode("utf8")).hexdigest()

        items["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        items["created"] = int(time.time())
        items["updated"] = int(time.time())
        items['is_deleted'] = 0

        # print("=============================================")
        # print(items)
        yield items
