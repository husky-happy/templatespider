# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5
import html
from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.item_check import check_item
website = 'ashleyfurniture'

class AshleyfurnitureSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['ashleyfurniture.com']
    # start_urls = ['http://ashleyfurniture.com/']

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
        super(AshleyfurnitureSpider, self).__init__(**kwargs)
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


    def filter_html_label(self, text):
        text = str(text)
        # 注释，js，css，html标签
        filter_rerule_list = [r'(<!--[\s\S]*?-->)', r'<script[\s\S]*?</script>', r'<style[\s\S]*?</style>', r'<[^>]+>']
        for filter_rerule in filter_rerule_list:
            html_labels = re.findall(filter_rerule, text)
            for h in html_labels:
                text = text.replace(h, ' ')
        filter_char_list = [
            u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000', u'\u200a', u'\u2028', u'\u2029', u'\u202f', u'\u205f',
            u'\u3000', u'\xA0', u'\u180E', u'\u200A', u'\u202F', u'\u205F', '\t', '\n', '\r', '\f', '\v',
        ]
        for f_char in filter_char_list:
            text = text.replace(f_char, '')
        text = html.unescape(text)
        text = re.sub(' +', ' ', text).strip()
        return text



    def start_requests(self):
        # url = "https://www.ashleyfurniture.com/p/home_accent_brim_13_gallon_50l_trash_can_with_lid/A600007038.html?cgid=kitchen-trash-and-recycling"
        url = "https://www.ashleyfurniture.com/p/machine_woven_anakara_53_x_73_area_rug/R600003690.html?cgid=style-lifestyle-new-traditions"
        yield scrapy.Request(
            url=url,
            # headers=self.headers
            callback=self.parse_detail,
        )


        url = "https://www.ashleyfurniture.com/"
        yield scrapy.Request(
            url=url,
            # headers=self.headers
        )

    def parse(self, response):
        url_list = response.xpath("//ul[@class='menu-category level-1']/li/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list if "javascript" not in url]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_kind,
            )

    def parse_kind(self, response):
        """列表页"""
        url_list = response.xpath("//a[@class='global-link']/@href").getall()
        url_list = [response.urljoin(url) for url in url_list if "javascript" not in url]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//a[@class='thumb-link']/@href").getall()
        url_list = [response.urljoin(url) for url in url_list if "javascript" not in url]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )

        next_page_url = response.xpath("//a[@rel='next']/@href").get()
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
        # price = re.findall("", response.text)[0]
        original_price = response.xpath("//div[@class='product-price']//del[@class='price-standard']/text()").get()
        if original_price:
            original_price = "".join(original_price).replace(" ", "").replace("\n", "").replace("$", "")
        current_price = response.xpath("//div[@class='product-price']//span[@class='sales-price']/text()").get()
        if current_price:
            current_price = current_price.replace(" ", "").replace("\n", "").replace("$", "")

        items["original_price"] = ""+str(original_price).replace("$", "") if original_price else ""+str(current_price)
        items["current_price"] = ""+str(current_price).replace("$", "") if current_price else ""+str(original_price)
        brand = re.findall('TurnToCatItemBrand = "(.*?)";', response.text)
        items["brand"] = brand[0] if brand else ''
        name = response.xpath("//h1[@itemprop='name']/text()").get()
        if name:
            items["name"] = self.filter_html_label(name)
        # items["about"] = response.xpath("").get()
        description_list = response.xpath("//h3[contains(text(), 'Description')]/../text()").getall()
        if description_list:
            items["description"] = self.filter_html_label("".join(description_list))
        items["source"] = website
        images_list = response.xpath("//div[contains(text(), 'Images')]/../ul//img/@src").getall()
        if images_list:
            images_list = images_list[:round(len(images_list)/2)]
        items["images"] = images_list

        Breadcrumb_list = response.xpath("//ol[@class='breadcrumb']/li/a/text()").getall()
        items["cat"] = items["name"]
        items["detail_cat"] = self.filter_html_label("/".join(Breadcrumb_list) + '/' + items["name"])
        sku_list = list()

        color_list = response.xpath('//div[@class=" pdp-redesign"]//div[@data-attr-id="color"]//li/a/@title').getall()
        size_list = response.xpath('//div[@class=" pdp-redesign"]//div[@data-attr-id="size4"]//option[not (contains(text(),"Select"))]/text()').getall()
        if color_list and size_list:
            for color in color_list:
                if self.filter_html_label(color):
                    for size in size_list:
                        SAI = SkuAttributesItem()
                        SAI['colour'] = self.filter_html_label(color)
                        SAI['size'] = self.filter_html_label(size)
                        SI = SkuItem()
                        SI['attributes'] = SAI
                        SI['imgs'] = []
                        SI['url'] = items['url']
                        SI['original_price'] = items['original_price']
                        SI['current_price'] = items['current_price']
                        sku_list.append(SI)
        elif not color_list and size_list:
            for size in size_list:
                SAI = SkuAttributesItem()
                SAI['size'] = self.filter_html_label(size)
                SI = SkuItem()
                SI['attributes'] = SAI
                SI['imgs'] = []
                SI['url'] = items['url']
                SI['original_price'] = items['original_price']
                SI['current_price'] = items['current_price']
                sku_list.append(SI)
        elif color_list and not size_list:
            for color in color_list:
                if self.filter_html_label(color):
                    SAI = SkuAttributesItem()
                    SAI['colour'] = self.filter_html_label(color)
                    SI = SkuItem()
                    SI['attributes'] = SAI
                    SI['imgs'] = []
                    SI['url'] = items['url']
                    SI['original_price'] = items['original_price']
                    SI['current_price'] = items['current_price']
                    sku_list.append(SI)



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

        # check_item(items)
        print(items)
        yield items
