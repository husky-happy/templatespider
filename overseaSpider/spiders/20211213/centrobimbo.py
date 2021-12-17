# -*- coding: utf-8 -*-
import html
import itertools
import re
import json
import time
import scrapy
import requests
from hashlib import md5
from scrapy.selector import Selector
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

# !/usr/bin/env python
# -*- coding: UTF-8 -*-
'''=================================================
@Project -> File   ：templatespider -> centrobimbo
@IDE    ：PyCharm
@Author ：Mr. Husky
@Date   ：2021/12/14 16:01
@Desc   ：
=================================================='''

website = 'centrobimbo'


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
    allowed_domains = ['centrobimbo.eu']
    start_urls = ['https://www.centrobimbo.eu/']

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
                       '¥']
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
        category_urls = ['https://www.centrobimbo.eu/content/6-marchi']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_brand)

    def parse_brand(self, response):
        category_urls = response.xpath("//section[@id='content']/p/a/@href").getall()
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='tvproduct-img-block-color-box']/a/@href").getall()
        # detail_url_list = ['https://www.centrobimbo.eu/scuola/2606-597-zaino-estensibile-go-pop-.html#/278-gopop_2020-fashion',
        #                    'https://www.centrobimbo.eu/pannolini/1351-354-trudi-pannolini-dry-fit.html',
        #                    'https://www.centrobimbo.eu/scuola/2635-692-bustina-gosmart.html']
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//a[@rel='next']/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//div[@class='product-prices']//span[@itemprop='price']/@content").get()
        items["original_price"] = price
        items["current_price"] = price

        name = response.xpath("//h1[@class='tvproduct-content-title']/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ol/li/a/span/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='product-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        # attr1_list = response.xpath("//div[@class='single-car-data']/table//tr/td[1]/text()").getall()
        # attr2_list = response.xpath("//div[@class='single-car-data']/table//tr/td[2]/text()").getall()
        # attribute = []
        # for a in range(len(attr1_list)):
        #     attribute.append(attr1_list[a] + ":" + attr2_list[a])
        # items["attributes"] = attribute

        images_list = response.xpath("//ul[@class='product-images js-qv-product-images']/li/img/@src").getall()
        items["images"] = images_list
        items["brand"] = ''

        opt_name = response.xpath("//div[@class='product-variants']/div/span/text()").getall()
        if not opt_name:
            items["sku_list"] = []
        else:
            for o in range(len(opt_name)):
                opt_name[o] = opt_name[o].replace("\n", "")
                opt_name[o] = opt_name[o].replace(":", "")
                opt_name[o] = opt_name[o].strip()
            product_id = response.xpath("//input[@name='id_product' and @id='product_page_product_id']/@value").get()
            attr_dict = dict()
            value_dict = dict()
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/select/option/@title").getall()
                if len(value_temp)==0:
                    value_temp = response.xpath(
                        "//div[@class='product-variants']/div["+str(i+1)+"]/ul/li/label/span/span/text()").getall()
                value_value = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/select/option/@value").getall()
                if len(value_value)==0:
                    value_value = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/ul/li/label/input/@value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]] = value_value[v]
                attr_name = response.xpath(
                    "//div[@class='product-variants']/div["+str(i+1)+"]/select/@name").get()
                if not attr_name:
                    attr_name = response.xpath("//div[@class='product-variants']/div["+str(i+1)+"]/ul/li/label/input/@name").get()
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
                'authority': 'www.centrobimbo.eu',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'x-requested-with': 'XMLHttpRequest',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://www.centrobimbo.eu',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                'cookie': 'PrestaShop-f1f25bbe0eec806639828a473fe7ded1=def502005c55709608cf64d9d5dddafbd18c02b5429ff08db91ece98b7b86dd2509f21009fb76002130d60e248f0382e30e3a6b37cc7d1254f799402afe3463fb35dd37a2e3191b8a2a0dbcc9864920ba003c58d4b250c177a84a346e489c28642ad64883393ff17fe77ae9414fe8d41043d9e2828e874c11d3b5b6f855674c63387b122a4e7fcc4d5d867ca374280e6b28108edf5fadbe901c8ab2ddb4eb1; _ga=GA1.2.381331834.1639381057; PHPSESSID=bc3c4d8d57fb79a81d478623910bc255; _gid=GA1.2.428670982.1639467815',
            }
            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()
                params = {
                    'controller': 'product',
                    'token': 'dee4abd8e20574f235a514cbbe87330f',
                    'id_product': product_id,
                    'id_customization': '0',
                    # 'group[67]': '279',
                    'qty': '1'
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
                    elif attr[0] == 'Colore':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                response1 = requests.post('https://www.centrobimbo.eu/index.php', headers=headers, params=params,
                                         data=data)
                sku_json = json.loads(response1.text)
                img_html = sku_json["product_cover_thumbnails"]
                new_response = Selector(text=img_html)
                img_list = new_response.xpath("//ul/li/img/@src").getall()
                sku_info["current_price"] = items["current_price"]
                sku_info["original_price"] = items["original_price"]
                sku_info["attributes"] = sku_attr
                sku_info["imgs"] = img_list

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
