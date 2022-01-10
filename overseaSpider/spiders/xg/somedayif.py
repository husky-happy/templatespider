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

website = 'somedayif'

class SomedayifSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['somedayif.com']
    start_urls = ['http://www.somedayif.com/']

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
        super(SomedayifSpider, self).__init__(**kwargs)
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

    def parse(self, response):
        """获取全部分类"""
        category_name = response.xpath("//div[@class='category mobiledisplaynone']/ul/li/a/text()").getall()[:13]
        category_url = response.xpath("//div[@class='category mobiledisplaynone']/ul/li/a/@href").getall()[:13]
        for i in range(len(category_name)):
            yield scrapy.Request(
                url='http://www.somedayif.com' + category_url[i],
                callback=self.parse_list,
                meta={"cat": category_name[i]}
            )


    def parse_list(self, response):
        """商品列表页"""
        detail_url = response.xpath("//ul[@class='thumbnail']/li/div/a/@href").getall()
        for i in detail_url:
            yield scrapy.Request(
                url='http://www.somedayif.com' + i,
                callback=self.parse_detail,
                meta={"cat": response.meta.get("cat")}
            )
        next_url = response.xpath(
            "//a[text()='Next' and @href!='#none']/@href").get()
        if next_url:
            yield scrapy.Request(
                url='http://www.somedayif.com/product/list.html'+next_url,
                callback=self.parse_list,
                meta={"cat": response.meta.get("cat")}
            )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        items["name"] = response.xpath("//meta[@property='og:title'][2]/@content").get()
        items["detail_cat"] = response.meta.get("cat") + '/' + items["name"]
        items["cat"] = items["name"]
        description = response.xpath("//meta[@property='og:description']/@content").get()
        items["description"] = description
        items["source"] = 'https://www.somedayif.com/'
        items["brand"] = 'SOMEDAY IF'
        image_temp = response.xpath("//div[@class='style-slide']/div/div/a/img/@src").getall()
        image = []
        for i in image_temp:
            if i.endswith('jpg'):
                if i.startswith('//'):
                    image.append('http:' + i)
                elif i.startswith('/'):
                    image.append('http://www.somedayif.com' + i)
        items["images"] = image

        items["current_price"] = response.xpath("//meta[@property='product:sale_price:amount']/@content").get()
        items["original_price"] = response.xpath("//meta[@property='product:price:amount']/@content").get()
        items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]

        opt_name = response.xpath(
            "//div[@class='product-option']/ul/li/label/text()").getall()
        opt_value = []
        for i in range(10):
            value_temp = response.xpath(
                "//select[@id='product_option_id" + str(i) + "']//text()").getall()
            if value_temp:
                opt_value.append(value_temp[2:])

        attrs_list = []
        for opt in itertools.product(*opt_value):
            temp = dict()
            for i in range(len(opt)):
                temp[opt_name[i]] = opt[i]
            if len(temp):
                attrs_list.append(temp)

        sku_list = list()
        for attrs in attrs_list:
            sku_info = SkuItem()
            sku_attr = SkuAttributesItem()
            other_temp = dict()
            for attr in attrs.items():
                if attr[0] == 'color' or attr[0] == 'Color' or attr[0] == 'COLOR' or attr[0] == 'colour' or \
                        attr[0] == 'Colour' or attr[0] == 'COLOUR':
                    sku_attr["colour"] = attr[1]
                elif attr[0] == 'size' or attr[0] == 'Size' or attr[0] == 'SIZE':
                    sku_attr["size"] = attr[1]
                elif attr[0] == 'color-size':
                    index = attr[1].index('-')
                    sku_attr["colour"] = attr[1][:index]
                    sku_attr["size"] = attr[1][index + 1]
                else:
                    other_temp[attr[0]] = attr[1]
            if len(other_temp):
                sku_attr["other"] = other_temp
            sku_info["current_price"] = items["current_price"]
            sku_info["original_price"] = items["original_price"]
            sku_info["attributes"] = sku_attr
            sku_list.append(sku_info)

        items["sku_list"] = sku_list

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
