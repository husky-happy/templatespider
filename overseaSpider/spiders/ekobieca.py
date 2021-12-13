# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'ekobieca'
scheme = 'https://www.ekobieca.pl'


class EkobiecaSpider(scrapy.Spider):
    name = website
    allowed_domains = ['ekobieca.pl']
    start_urls = ['https://www.ekobieca.pl/']

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
        super(EkobiecaSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "方尘")

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

    def parse(self, response):
        """获取全部分类"""
        category_urls = response.xpath("//ul[@class='dl-menu']/li/a/@href").getall()
        for category_url in category_urls:
            if not category_url.startswith('http'):
                category_url = scheme + category_url
            yield scrapy.Request(
                url=category_url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//a[@class='product-icon align_row']/@href").getall()
        for detail_url in detail_url_list:
            if not detail_url.startswith('http'):
                detail_url = scheme + detail_url
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_detail
            )
        next_page_url = response.xpath('//div[@class="search_paging_sub"]/a[@class="next"]/@href').get()
        if next_page_url:
            if not next_page_url.startswith('http'):
                next_page_url = scheme + next_page_url
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        current_price = response.xpath("//strong[@class='projector_price_value']/text()").get()
        original_price = response.xpath("//div[@id='projector_price_maxprice_wrapper']/del/text()").get()
        items["current_price"] = current_price.replace('.', '').replace(',', '.')
        items["original_price"] = original_price or items["current_price"]

        items["name"] = response.xpath("//div[@class='projector_navigation']/h1[1]/text()").get()

        cat_list = response.xpath('//div[@id="breadcrumbs_sub"]/ol/li//text()').getall()
        cat_list = [cat.strip() for cat in cat_list if cat.strip()]
        items["detail_cat"] = '/'.join(cat_list)
        items["cat"] = cat_list[-1]

        brand = re.search(r'"brand": "(.*?)",', response.text).group(1)
        if brand:
            items["brand"] = brand.group(1)

        description = response.xpath("//div[contains(@class, 'longdescription_wrapper')]").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        items["sku_list"] = []

        items["images"] = response.xpath('//ul[@class="bxslider"]/li/a/img/@src').getall()

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
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        print(items)
        yield items
