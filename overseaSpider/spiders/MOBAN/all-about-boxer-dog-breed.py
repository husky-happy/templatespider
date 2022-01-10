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
@Project -> File   ：templatespider -> exclusivedogsupplies
@IDE    ：PyCharm
@Author ：Mr. Husky
@Date   ：2021/12/28 11:10
@Desc   ：
=================================================='''

website = 'all-about-boxer-dog-breed1'
website_url = 'https://www.all-about-boxer-dog-breed.com/'

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
    allowed_domains = ['all-about-boxer-dog-breed.com']
    start_urls = ['https://www.all-about-boxer-dog-breed.com/']

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
        category_urls = response.xpath("//ul[@class='nav navbar-nav mn1']/li[not(@class) and not(@id)][position()<5]/a/@href").getall()
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@id='product-area']/div//div[@class='product__inside']/div/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//li[@class='pagination-next']/a/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//div[@id='productPrices']/span/text()").get()
        price = self.price_fliter(price)
        items["original_price"] = price
        items["current_price"] = items["original_price"]

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ol/li/a/text()").getall()
        cat_list.append(name)
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//meta[@name='description']/@content").get()
        items["description"] = description
        items["source"] = 'all-about-boxer-dog-breed.com'

        # attr1_list = response.xpath("//div[@class='single-car-data']/table//tr/td[1]/text()").getall()
        # attr2_list = response.xpath("//div[@class='single-car-data']/table//tr/td[2]/text()").getall()
        # attribute = []
        # for a in range(len(attr1_list)):
        #     attribute.append(attr1_list[a] + ":" + attr2_list[a])
        # items["attributes"] = attribute

        img_str = response.xpath("//div[@class='back product-main-image__item main-img-lightbox']/script/text()").get()
        if not img_str:
            return
        html = re.search(r'href="(.*?)"><',img_str,re.S).group(1)
        html = website_url + html
        images_list = [html]
        items["images"] = images_list

        items["brand"] = ''

        sku_variant = response.xpath("//div[@id='productAttributes']/div[@class='wrapperAttribsOptions']/span")
        # opt_name = response.xpath("//div[@id='productAttributes']/div[@class='wrapperAttribsOptions']/span[@class='option-label']//text()").getall()
        if len(sku_variant)<1:
            items["sku_list"] = []
        else:
            opt_name = []
            product_id = response.xpath("//input[@name='products_id']/@value").get()
            attr_dict = dict()
            value_dict = dict()
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            for sku in sku_variant:
                opt_name.append(sku.xpath(".//text()").get())
                value_temp = sku.xpath("../div//select/option/text()").getall()
                if not value_temp:
                    value_temp = sku.xpath("../div//label/text()").getall()
                value_value = sku.xpath("../div//input/@value").getall()
                if not value_value:
                    value_value = sku.xpath("../div//select/option/@value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]] = value_value[v]
                attr_name = sku.xpath("../div//select/@name").get()
                if not attr_name:
                    attr_name = sku.xpath("../div//div[@class='attribute_options']/input/@name").get()
                attr_dict[opt_name[-1]] = attr_name
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
            cookies = {
                '_ga': 'GA1.2.1347353784.1640591905',
                '_gid': 'GA1.2.1180225371.1640591905',
                'velaro_firstvisit': '%222021-12-27T07%3A58%3A37.727Z%22',
                'velaro_visitorId': '%22VWQ0ppgXlEitDosVbyc4nw%22',
                'zenid': '7c3facb73c78c65fe80a03f7f2c6147d',
                'velaro_endOfDay': '%222021-12-28T23%3A59%3A59.999Z%22',
                '_gat': '1',
                '__atuvc': '3%7C52',
                '__atuvs': '61cab68e101a6222001',
            }

            headers = {
                'Connection': 'keep-alive',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua-mobile': '?0',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'sec-ch-ua-platform': '"Windows"',
                'Accept': '*/*',
                'Origin': 'https://www.all-about-boxer-dog-breed.com',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Dest': 'empty',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
            }

            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()
                params = {
                    'products_id': product_id,
                    # 'cPath': '5',
                    'number_of_uploads': '0',
                    'act': 'DPU_Ajax',
                    'method': 'dpu_update',
                }

                data = {
                    'securityToken': '44aec2cb88d50a9c192fb50fc795ba87',
                    # 'id[87]': '863',
                    # 'id[92]': '908',
                    # 'id[88]': '881',
                    # 'id[101]': '1545',
                    'cart_quantity': '1',
                    'products_id': product_id,
                    'pspClass': 'productGeneral price-box product-info__price',
                    'stat': 'main',
                    'outputType': 'XML'
                }
                for attr in attrs.items():
                    data[attr_dict[attr[0]]] = value_dict[attr[1]]
                    if attr[0].find("Size") != -1:
                        sku_attr["size"] = attr[1]
                    elif attr[0].find('Color')!=-1:
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                response = requests.post('https://www.all-about-boxer-dog-breed.com/ajax.php', headers=headers, params=params, cookies=cookies, data=data)
                html = Selector(text=response.text)
                sku_price = html.xpath("//span[@class='DPUSideboxTotalDisplay']/text()").get()
                # print(sku_price)
                sku_price = self.price_fliter(sku_price)
                # data_json = sku_json["data"]
                sku_info["current_price"] = sku_price
                sku_info["original_price"] = sku_price
                sku_info["url"] = items["url"]
                sku_info["attributes"] = sku_attr
                # if "image" in data_json:
                #     if data_json["image"] is not None:
                #         img = data_json["image"]["data"]
                #         img = img.replace("{:size}", "1280x1280")
                #         img_list = [img]
                #         sku_info["imgs"] = img_list

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
        # detection_main(items=items, website=website, num=3, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
