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
@Project -> File   ：templatespider -> sophisticatedpup
@IDE    ：PyCharm
@Author ：Mr. Husky
@Date   ：2021/12/28 10:14
@Desc   ：
=================================================='''

website = 'sophisticatedpup'


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
    allowed_domains = ['sophisticatedpup.com']
    start_urls = ['https://www.sophisticatedpup.com/']

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
        category_urls = response.xpath("//ul[@class='navPages-list']/li[position()<13]/a/@href").getall()
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//li[@class='product']/article/figure/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//li[@class='pagination-item pagination-item--next']/a/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price = response.xpath("//div[@class='productView-price']//span[@class='price price--withoutTax']/text()").get()
        price = price if '-' not in price else price.split('-')[0]
        price = self.price_fliter(price)
        items["original_price"] = price
        items["current_price"] = items["original_price"]

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumbs']/li//span/text()").getall()
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@id='tab-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = 'sophisticatedpup.com'

        # attr1_list = response.xpath("//div[@class='single-car-data']/table//tr/td[1]/text()").getall()
        # attr2_list = response.xpath("//div[@class='single-car-data']/table//tr/td[2]/text()").getall()
        # attribute = []
        # for a in range(len(attr1_list)):
        #     attribute.append(attr1_list[a] + ":" + attr2_list[a])
        # items["attributes"] = attribute

        images_list = response.xpath("//ul[@class='productView-thumbnails']/li/a/@href").getall()
        items["images"] = images_list

        items["brand"] = ''

        opt_name_tmp = response.xpath(
            "//div[@data-product-option-change]/div/label[@class='form-label form-label--alternate form-label--inlineSmall']/text()").getall()
        opt_name = []
        for o in opt_name_tmp:
            if o.find(":") != -1:
                opt_name.append(o)
        if not opt_name:
            items["sku_list"] = []
        else:
            for o in range(len(opt_name)):
                opt_name[o] = opt_name[o].replace("\n", "")
                opt_name[o] = opt_name[o].replace(":", "")
                opt_name[o] = opt_name[o].strip()
            product_id = response.xpath("//input[@name='product_id']/@value").get()
            attr_dict = dict()
            value_dict = dict()
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@data-product-option-change]/div[" + str(
                    i + 1) + "]/label[@class='form-option']/span/text()").getall()
                value_value = response.xpath(
                    "//div[@data-product-option-change]/div[" + str(i + 1) + "]/input/@value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]] = value_value[v]
                attr_name = response.xpath(
                    "//div[@data-product-option-change]/div[" + str(i + 1) + "]/input/@name").get()
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
                'authority': 'www.sophisticatedpup.com',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'stencil-config': '{}',
                'x-xsrf-token': '8326ca8f28e7ffb1856f9baa12cb8884b5c8b02239985a08936d39a29989130a, 8326ca8f28e7ffb1856f9baa12cb8884b5c8b02239985a08936d39a29989130a',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'accept': '*/*',
                'x-requested-with': 'XMLHttpRequest',
                'stencil-options': '{"render_with":"products/bulk-discount-rates"}',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://www.sophisticatedpup.com',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                'cookie': 'SHOP_SESSION_TOKEN=q54um0idh1uc4nepb7pucplih6; fornax_anonymousId=c4f8741c-faae-4234-96dc-aef84770a5c3; XSRF-TOKEN=8326ca8f28e7ffb1856f9baa12cb8884b5c8b02239985a08936d39a29989130a; LD_T=52ad7869-c102-4f50-eea9-bf63a5bd9491; LD_U=https%3A%2F%2Fwww.sophisticatedpup.com%2F; LD_R=http%3A%2F%2F20.81.114.208%3A8000%2F; _ga=GA1.2.956474976.1640657222; _gid=GA1.2.565965290.1640657222; __utma=264507789.956474976.1640657222.1640657222.1640657222.1; __utmc=264507789; __utmz=264507789.1640657222.1.1.utmcsr=20.81.114.208:8000|utmccn=(referral)|utmcmd=referral|utmcct=/; STORE_VISITOR=1; distinct_id=25301_1640657224788_5511; cbox_second_page_popup_was_closed=0; cbox_condition_popup_status=1; bk_bc_cart_token=25301_1640657225717_6453; bk_cart={%22t%22:%2225301_1640657225717_6453%22%2C%22s%22:[]%2C%22a%22:[]%2C%22i%22:[]}; cbox_first_page_popup_was_closed=1; cbox_new_visitor={%22status%22:false%2C%22created_at%22:1640657225627}; lastVisitedCategory=59; LD_S=1640658501473; __utmt=1; Shopper-Pref=44365CA12DE43481D95385C9CB2AE07FE196A451-1641263375888-x%7B%22cur%22%3A%22USD%22%7D; __atuvc=15%7C52; __atuvs=61ca71649b91322500e; __utmb=264507789.31.10.1640657222; _gat=1',
            }
            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()
                data = {
                    'action': 'add',
                    'product_id': product_id,
                    'qty[]': '1'
                }
                for attr in attrs.items():
                    data[attr_dict[attr[0]]] = value_dict[attr[1]]
                    if attr[0].find("Size") != -1:
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Color':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                response = requests.post('https://www.sophisticatedpup.com/remote/v1/product-attributes/'+product_id, headers=headers, data=data)
                sku_json = json.loads(response.text)
                data_json = sku_json["data"]
                sku_info["current_price"] = str(data_json["price"]["without_tax"]["value"])
                if "rrp_without_tax" in data_json["price"]:
                    sku_info["original_price"] = str(data_json["price"]["rrp_without_tax"]["value"])
                else:
                    sku_info["original_price"] = str(data_json["price"]["without_tax"]["value"])
                sku_info["url"] = response.url
                sku_info["attributes"] = sku_attr
                if "image" in data_json:
                    if data_json["image"] is not None:
                        img = data_json["image"]["data"]
                        img = img.replace("{:size}", "1280x1280")
                        img_list = [img]
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
