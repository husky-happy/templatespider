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

website = 'schoolsuppliescatalog'


def get_sku_price(product_id, attribute_list):
    """获取sku价格"""
    url = 'https://thecrossdesign.com/remote/v1/product-attributes/{}'.format(product_id)
    data = {
        'action': 'add',
        'product_id': product_id,
        'qty[]': '1',
    }
    for attribute in attribute_list:
        data['attribute[{}]'.format(attribute[0])] = attribute[1]
    response = requests.post(url=url, data=data)
    return json.loads(response.text)['data']['price']['without_tax']['formatted']


class ThecrossdesignSpider(scrapy.Spider):
    name = website
    allowed_domains = ['schoolsuppliescatalog.com']
    start_urls = ['https://schoolsuppliescatalog.com/']

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
        super(ThecrossdesignSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "叶复")

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
        label_pattern = [r'<div class="cbb-frequently-bought-container cbb-desktop-view".*?</div>', r'(<!--[\s\S]*?-->)', r'<script>.*?</script>', r'<style>.*?</style>', r'<[^>]+>']
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
        category_urls = response.xpath("//div[contains(@class,'leo-top-menu')]//div[@class='dropdown-menu-inner']/div[@class='row']//div[@class='inner']/ul/li/a/@href").getall()
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='product-image']/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)

        # next_page_url = response.xpath("//a[@rel='next']/@href").get()
        # if next_page_url:
        #     yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//div[@class='current-price']/span/@content").get()
        items["original_price"] = price
        items["current_price"] = price

        name = response.xpath("//section[@id='main']//h1[@class='h1 product-detail-name']/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@itemscope]/li/a/span/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='product-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website
        items["brand"] = response.xpath("//span[@itemprop='brand']/@content").get()
        images_list = response.xpath("//ul[@class='product-images js-qv-product-images']/li[@class='thumb-container']/img/@data-image-large-src").getall()
        for i in range(len(images_list)):
            if images_list[i].find("http")==-1:
                images_list[i]="https:"+images_list[i]
        items["images"] = images_list
        label1 = response.xpath("//div[@class='data-table']/dl/dt/text()").getall()
        # print(label1)
        label2 = response.xpath("//div[@class='data-table']/dl/dd/text()").getall()
        # print(label2)
        attributes = []
        if label1:
            for i in range(len(label1)):
                if(label2[i]=='  '):
                    label2[i]= ''
                    str_json=re.search(r"var pfeatures = (.*?)}}},",response.text).group(1)
                    str_json = str_json+"}}}"
                    s_json = json.loads(str_json)
                    for j in s_json["2"]:
                        label2[i]=label2[i]+s_json["2"][j]['value']+','
                    if label2[i].endswith(","):
                        label2[i] = label2[i][:-1]
                s = label1[i]+":"+label2[i]
                attributes.append(s)
            items["attributes"]=attributes

        items["sku_list"] = []

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
        # print(items)
        yield items
