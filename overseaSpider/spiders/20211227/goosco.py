# -*- coding: utf-8 -*-
import html
import itertools
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
from scrapy.selector import Selector

# !/usr/bin/env python
# -*- coding: UTF-8 -*-
'''=================================================
@Project -> File   ：templatespider -> goosco
@IDE    ：PyCharm
@Author ：Mr. Husky
@Date   ：2021/12/27 16:31
@Desc   ：
=================================================='''

website = 'goosco'


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
    allowed_domains = ['goosco.com']
    start_urls = ['https://goosco.com/']

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

    def price_fliter(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ', '$', '€', ',', '\n',
                       '¥', '₺']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def filter_text(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', '\r\n\r\n', '/', '**', '>>', '\\n\\t\\t', '\\n        ',
                       '\\n\\t  ', '&#x27;', '`', '&lt;', 'p&gt;', 'amp;', 'b&gt;', '&gt;', 'br ', '$', '€']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse(self, response):
        """获取全部分类"""
        category_urls = ['https://goosco.com/20-shop-for-dogs',
                          'https://goosco.com/32-cats']

        category_cate = ['Dogs',
                         "Cats"]
        for c in range(len(category_urls)):
            yield scrapy.Request(url=category_urls[c], callback=self.parse_list, meta={"cat":category_cate[c]})

    def parse_list(self, response):
        """商品列表页"""
        cate = response.meta.get("cat")
        detail_url_list = response.xpath("//div[@class='products']/article/div/div[@class='thumbnail-container']/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail, meta={"cat":cate})
        next_page_url = response.xpath("//a[@rel='next']/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list, meta={"cat":cate})

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        cate = response.meta.get("cat")
        price = response.xpath("//span[@itemprop='price']/@content").get()

        items["original_price"] = price
        items["current_price"] = items["original_price"]

        name = response.xpath("//h1[@itemprop='name']/text()").get()
        items["name"] = name

        cat_list = ['Home',cate]
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='product-information']/div[@itemprop='description' and @id]").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = 'goosco.com'

        # attr1_list = response.xpath("//div[@class='single-car-data']/table//tr/td[1]/text()").getall()
        # attr2_list = response.xpath("//div[@class='single-car-data']/table//tr/td[2]/text()").getall()
        # attribute = []
        # for a in range(len(attr1_list)):
        #     attribute.append(attr1_list[a] + ":" + attr2_list[a])
        # items["attributes"] = attribute

        images_list = response.xpath("//ul[@id='js-qv-product-slider']/li/img/@data-image-large-src").getall()
        items["images"] = images_list
        items["brand"] = ''

        opt_name = response.xpath("//div[@class='product-variants']/div/span/text()").getall()

        if not opt_name:
            items["sku_list"] = []
        else:
            product_id = response.xpath("//div[@class='product-information']//input[@name='id_product']/@value").get()
            attr_dict = dict()
            value_dict = dict()
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/select/option/text()").getall()
                value_value = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/select/option/@value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]] = value_value[v]
                attr_name = response.xpath(
                    "//div[@class='product-variants']/div["+str(i+1)+"]/select/@name").get()
                attr_dict[opt_name[i]] = attr_name
                if value_temp:
                    opt_value.append(value_temp)
            # print(opt_value)
            attrs_list = []
            for opt in itertools.product(*opt_value):
                temp = dict()
                for i in range(len(opt)):
                    temp[opt_name[i]] = opt[i]
                if len(temp):
                    attrs_list.append(temp)
            # print(attrs_list)
            headers = {
                'authority': 'goosco.com',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'x-requested-with': 'XMLHttpRequest',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://goosco.com',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                'cookie': 'PHPSESSID=34ff20c558eb0e3dfe41afc9bf0eb109; PrestaShop-54cd96bc1a1280a704915f62283c3105=def50200f596965ce3b84285b6e883f8d57214263acb8b5c9edd7be68dc7379e49ffa915ef4111970fc15ba61812c65fa126529d392056b38af81e3ccd9f8981757922061f784b47e297b9f7a0a0054067a14fb1ab2433a4d3bd1b7c3f2dfa2be6a76c1b9f9e68ca8823a9dc8a026d41edf0604a9e4487b548378d3ff0c1178f340f9395da946012338ac7c1920edaa58cdde0a19d4cc55cb2bcf7353c64c19ac95d7eb2a4719fdb9de2d54bf8abc37381438e5f59f297ad1a9425035d96634543e51997bfd34f51731f18ef654807cc748f9f2b1a4a61b884c8b0e71f3907c41e',
            }
            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()
                params = {
                    'controller': 'product',
                    'token': '6fde097115ba82f8c16df4261584d5e6',
                    'id_product': product_id,
                    'qty': '1',
                }

                data = {
                    'ajax': '1',
                    'action': 'refresh',
                    'quantity_wanted': '1'
                }
                for attr in attrs.items():
                    params[attr_dict[attr[0]]] = value_dict[attr[1]]
                    if attr[0].find("Size") != -1:
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Color':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                response = requests.post('https://goosco.com/index.php', headers=headers, params=params, data=data)
                sku_json = json.loads(response.text)
                Html = sku_json["product_prices"]
                new_response = Selector(text=Html)
                sku_info["current_price"] = new_response.xpath("//span[@itemprop='price']/@content").get()
                sku_info["original_price"] = new_response.xpath("//span[@itemprop='price']/@content").get()
                sku_info["attributes"] = sku_attr
                sku_info["url"] = response.url

                sku_list.append(sku_info)
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
        # item_check.check_item(items)
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
