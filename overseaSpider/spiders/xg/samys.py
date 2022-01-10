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

website = 'samys'


class SamysSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['samys.com']
    start_urls = ['https://www.samys.com/']

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
        super(SamysSpider, self).__init__(**kwargs)
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
        category_url = ['https://www.samys.com/c/Photography/1/113.html',
                        'https://www.samys.com/c/Video/1/235.html',
                        'https://www.samys.com/c/Studio--Lighting/1/360.html',
                        'https://www.samys.com/c/Electronics/1/421.html',
                        'https://www.samys.com/c/Smartphone/1/830.html',
                        'https://www.samys.com/c/Pro-Cinema--Audio/2/794.html']
        for i in category_url:
            yield scrapy.Request(
                url=i,
                callback=self.parse_list,
                meta={"flag": 0}
            )

    def parse_list(self, response):
        """商品列表页"""
        detail_url = response.xpath("//div[@itemprop='name']/a/@href").getall()
        if detail_url:
            for i in detail_url:
                yield scrapy.Request(
                    url='https://www.samys.com'+i,
                    callback=self.parse_detail
                )
            if response.meta.get("flag") == 0:
                next_url = response.url + '?start=37'
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_list,
                    meta={"flag": 1, "start": 37, "url": response.url}
                )
            else:
                start = response.meta.get("start") + 36
                next_url = response.url + '?start=' + str(start)
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_list,
                    meta={"flag": 1, "start": start, "url": response.meta.get("url")}
                )
        else:
            category_url = response.xpath("//div[@class='category-container']/div/a/@href").getall()
            for i in category_url:
                yield scrapy.Request(
                    url='https://www.samys.com' + i,
                    callback=self.parse_list,
                    meta={"flag": 0}
                )

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        items["name"] = response.xpath('//meta[@property="og:title"]/@content').get()
        cat_temp = response.xpath("//ul[@class='breadcrumbs floatContainer']//a//text()").getall()
        items["detail_cat"] = '/'.join(cat_temp)
        items["cat"] = cat_temp[-1]
        des_temp=response.xpath('//span[@itemprop="description"]//text()').getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(des_temp)))
        items["source"] = 'samys.com'
        items["brand"] = response.xpath('//meta[@itemprop="brand"]/@content').get()
        image_temp=response.xpath("//ul[@class='slider-detail']/li/a/img/@src").getall()[:1]+response.xpath("//ul[@class='slider-detail']/li/a/img/@data-post-load-image").getall()
        if not image_temp:
            image_temp = response.xpath("//div[@class='swiper-slide false']/img/@src").getall()
        image=[]
        for i in image_temp:
            image.append('https://www.samys.com'+i)
        items["images"] = image
        items["current_price"] = response.xpath("//meta[@itemprop='price']/@content").get()
        items["original_price"] = items["current_price"]
        items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]

        items["sku_list"] =[]
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
