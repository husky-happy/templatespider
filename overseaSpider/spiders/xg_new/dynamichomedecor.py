# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.util.utils import isLinux, filter_text
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'dynamichomedecor'

class DynamichomedecorSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['dynamichomedecor.com']
    # start_urls = ['http://dynamichomedecor.com/']

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = True
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(DynamichomedecorSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "凯棋")

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
        url = "https://www.dynamichomedecor.com/"
        yield scrapy.Request(
           url=url,
        )

    def parse(self, response):
        url_list = response.xpath("//ul[@id='css3menu1']/li/div//ul/li/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            url = url + "?Per_Page=96&CatListingOffset=0"
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//div[@class='row']//div[@class='category-item']/div/a/@href").getall()
        if url_list:
            url_list = [response.urljoin(url) for url in url_list]
            for url in url_list:
                # print(url)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                )

            split_str = 'CatListingOffset='
            base_url = response.url.split(split_str)[0]
            page_num = int(response.url.split(split_str)[1])+1
            next_page_url = base_url + split_str + str(page_num)
            if next_page_url:
               next_page_url = response.urljoin(next_page_url)
               print("下一页:"+next_page_url)
               yield scrapy.Request(
                   url=next_page_url,
                   callback=self.parse_list,
               )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        Availability = response.xpath("//span[@class='dhd-orange']/b/text()").get()
        if Availability == 'IN STOCK':
            # price = re.findall("", response.text)[0]
            original_price = response.xpath("//span[@id='price-value']/text()").get().replace("\r", "")
            current_price = response.xpath("//span[@id='price-value']/text()").get().replace("\r", "")
            items["original_price"] = "" + str(original_price) if original_price else "" + str(current_price)
            items["current_price"] = "" + str(current_price) if current_price else "" + str(original_price)
            items["brand"] = response.xpath("//span[@itemprop='brand']/text()").get()
            items["name"] = response.xpath("//span[@itemprop='name']/text()").get()
            # attributes = list()
            # items["attributes"] = attributes
            # items["about"] = response.xpath("").get()
            description_list = response.xpath("//div[@id='description']/span//text()").getall()
            items["description"] = filter_text("".join(description_list))
            # items["care"] = response.xpath("").get()
            # items["sales"] = response.xpath("").get()
            items["source"] = website

            # images_list = response.xpath("//div[@class='mcs-items-container']/div/a/@href").getall()
            images_list = list()
            img_list = re.findall("image_data\":([\s\S]*?)\}", response.text)
            if img_list:
                for img in img_list:
                    image_str_list = img.replace("\n", "")
                    image_list = json.loads(image_str_list)
                    image_list = ["https://www.dynamichomedecor.com/mm5/" + i for i in image_list if "1000x1000" in i]
                    if image_list:
                        images_list.append(image_list[0])
            else:
                images_list = response.xpath("//meta[@itemprop='image']/@content").getall()
            items["images"] = images_list
            Breadcrumb_list = response.xpath("//ul[@class='breadcrumb']/li//text()").getall()
            items["cat"] = Breadcrumb_list[-2]
            items["detail_cat"] = "/".join(Breadcrumb_list)

            sku_list = list()
            sku_info_list = response.xpath("//select[@class='form-control']/option/@value").getall()
            if sku_info_list:
                for sku in sku_info_list:
                    sku_item = SkuItem()
                    sku_item["original_price"] = items["original_price"]
                    sku_item["current_price"] = items["current_price"]
                    sku_item["url"] = response.url
                    attributes = SkuAttributesItem()
                    # attributes["colour"] = sku["name"]
                    # attributes["size"] = sku["size"]
                    other = dict()
                    other["option"] = sku
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

            print(items)
            yield items
