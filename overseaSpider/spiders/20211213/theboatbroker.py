# -*- coding: utf-8 -*-
import html
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'theboatbroker'


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
    allowed_domains = ['theboatbroker.com']
    start_urls = ['https://www.theboatbroker.com/']

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

    def filter_html_label(self, text):
        text = str(text)
        text = html.unescape(text)
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
        text = re.sub(' +', ' ', text).strip()
        return text

    def filter_text(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ','$']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls = response.xpath("//div[@class='main-menu']/ul[@class='header-menu clearfix']/li[position()>1 and position()<6]/ul/li/a/@href").getall()
        category_cat = response.xpath("//div[@class='main-menu']/ul[@class='header-menu clearfix']/li[position()>1 and position()<6]/ul/li/a/text()").getall()
        for i in range(len(category_urls)):
            yield scrapy.Request(url=category_urls[i], callback=self.parse_list, meta={"cat": category_cat[i]})

    def parse_list(self, response):
        """商品列表页"""
        cate = response.meta.get("cat")
        detail_url_list = response.xpath("//div[@class='title heading-font']/a[@class='rmv_txt_drctn']/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail, meta={"cat": cate})

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        cate = response.meta.get("cat")
        price_new = response.xpath("//span[@class='h3']/text()").get()
        if not price_new:
            price_new = response.xpath("//div[@class='h4']/text()").get()
        if price_new.find("PRICE")!=-1:
            return
        price_new = self.filter_text(price_new)
        price_new = price_new.replace(" ,",'')
        price_old = response.xpath("//div[@class='regular-price-with-sale']/strong/text()").get()
        if price_old:
            price_old = self.filter_text(price_old)
            price_old = price_old.replace("\n",'')
            price_old = price_old.replace(" ,",'')
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h2/text()").get()
        name = self.filter_text(name)
        items["name"] = name

        cat_list = [cate,name]
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[contains(@class,'wpb_text_column wpb_content_element')]/div[@class='wpb_wrapper']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website
        attr1_list = response.xpath("//div[@class='single-car-data']/table//tr/td[1]/text()").getall()
        attr2_list = response.xpath("//div[@class='single-car-data']/table//tr/td[2]/text()").getall()
        attribute = []
        for a in range(len(attr1_list)):
            attribute.append(attr1_list[a]+":"+attr2_list[a])
        items["attributes"] = attribute

        images_list = response.xpath("//div[@class='media-carousel-item']/a/@href").getall()
        if len(images_list)==0:
            return
        items["images"] = images_list
        items["brand"] = ''

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
        item_check.check_item(items)
        detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
