# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
import itertools
from lxml import etree
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'dekanta'


class DekantaSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['dekanta.com']
    start_urls = ['https://dekanta.com/']

    @classmethod
    def update_settings(cls, settings):
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(DekantaSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "无穹")

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': True,
        # 'HTTPCACHE_EXPIRATION_SECS': 14 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            # 'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
    }

    def filter_html_label(self, text):  # 洗description标签函数
        label_pattern = [r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
        for pattern in label_pattern:
            labels = re.findall(pattern, text, re.S)
            for label in labels:
                text = text.replace(label, '')
        text = text.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '').strip()
        return text

    def filter_text(self, input_text):
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def start_requests(self):
        """获取全部分类"""
        category_url = ['https://dekanta.com/store/', 'https://dekanta.com/product-category/exotic-spirits/']
        for i in category_url:
            yield scrapy.Request(
                url=i,
                callback=self.parse_list
            )

    def parse_list(self, response):
        """商品列表页"""
        detail_url = response.xpath("//div[@class='image-none']/a/@href").getall()
        for i in detail_url:
            yield scrapy.Request(
                url=i,
                callback=self.parse_detail
            )
        next_url = response.xpath("//a[@class='next page-number']/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        items["name"] = response.xpath("//h1[@class='product-title entry-title']/text()").get()
        cat_temp = response.xpath("//nav[@class='woocommerce-breadcrumb breadcrumbs']/a/text()").getall()
        items["detail_cat"] = '/'.join(cat_temp)
        items["cat"] = cat_temp[-1]
        items["description"] = response.xpath("//meta[@name='description']/@content").get()
        if not items["description"]:
            items["description"]=''
        items["source"] = website
        items["brand"] = re.search('"Brand","name":"(.*?)"', response.text).group(1)
        items["images"] = response.xpath("//div[@class='first slide woocommerce-product-gallery__image']/a/@href").getall()+\
                          response.xpath("//div[@class='woocommerce-product-gallery__image slide']/a/@href").getall()
        prz_temp=response.xpath("//p[@class='price product-page-price ']/span/span/text()").get()
        if not prz_temp:
            return
        items["current_price"] = prz_temp
        items["original_price"] = items["current_price"]
        items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]

        items["sku_list"] = []
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
        # detection_main(items=items, website=website, num=20, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
