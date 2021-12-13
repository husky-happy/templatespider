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

website = 'signalboosters'


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
    allowed_domains = ['signalboosters.com']
    start_urls = ['https://www.signalboosters.com/']

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
        category_urls = ['https://www.signalboosters.com/consumer/home',
                         'https://www.signalboosters.com/consumer/vehicle',
                         'https://www.signalboosters.com/consumer/small-business',
                         'https://www.signalboosters.com/consumer/commercial-buildings',
                         'https://www.signalboosters.com/cellular-hotspot-expansion-kits/',
                         'https://www.signalboosters.com/consumer/refurbished']
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//h4[@class='listItem-title']/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//li[@class='pagination-item pagination-item--next']/a/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_new = response.xpath("//section[@class='productView-details']//span[@class='price price--withoutTax']/text()").get()
        if not price_new:
            return
        price_new = self.filter_text(price_new)
        price_new = price_new.replace(",",'')
        price_old = response.xpath("//section[@class='productView-details']//span[@class='price price--rrp']/text()").get()
        if price_old:
            price_old = self.filter_text(price_old)
            price_old = price_old.replace(",",'')
            items["original_price"] = price_old
        else:
            price_old = response.xpath("//div[@class='productView-priceMSRP']//text()").get()
            if price_old:
                price_old = self.filter_text(price_old)
                price_old = price_old.replace(",", '')
                items["original_price"] = price_old
            else:
                items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumbs']/li/a/text()").getall()
        cat_list.append(name)
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='about-intro']/div[@class='columns two-columns']/div[1]").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list_tmp = response.xpath("//ul[@class='productView-thumbnails']/li/a/@href").getall()
        images_list = []
        for i in images_list_tmp:
            if i.find("void(0)")==-1:
                images_list.append(i)
        if len(images_list)==0:
            images_list = response.xpath("//figure[@class='productView-image']/img/@src").getall()
        items["images"] = images_list
        brand = response.xpath("//div[@data-product-brand]/@data-product-brand").get()
        items["brand"] = brand

        opt_name_tmp = response.xpath("//div[@class='productView-optionsList']/div/div/label/text()").getall()
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
            # print(opt_name)
            product_id = response.xpath("//input[@name='product_id']/@value").get()
            attr_dict = dict()
            value_dict = dict()
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@class='productView-optionsList']/div/div["+str(i+1)+"]/select/option[@data-product-attribute-value]/text()").getall()
                if not value_temp:
                    value_temp = response.xpath("//div[@class='productView-optionsList']/div/div["+str(i+1)+"]/label/span/text()").getall()
                value_value = response.xpath("//div[@class='productView-optionsList']/div/div["+str(i+1)+"]/select/option[@data-product-attribute-value]/@value").getall()
                if not value_value:
                    value_value = response.xpath("//div[@class='productView-optionsList']/div/div["+str(i+1)+"]/input/@value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]] = value_value[v]
                attr_name = response.xpath(
                    "//div[@class='productView-optionsList']/div/div["+str(i+1)+"]/select/@name").get()
                if not attr_name:
                    attr_name = response.xpath("//div[@class='productView-optionsList']/div/div["+str(i+1)+"]/input/@name").get()
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
                'authority': 'www.signalboosters.com',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'stencil-config': '{}',
                'x-xsrf-token': '473a099babe808b4fe83ab47313788ad5df62931b064f7183916a32084c6f9ad, 473a099babe808b4fe83ab47313788ad5df62931b064f7183916a32084c6f9ad',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'accept': '*/*',
                'x-requested-with': 'XMLHttpRequest',
                'stencil-options': '{}',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://www.signalboosters.com',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                'cookie': 'layer0_bucket=61; layer0_destination_info=default; layer0_environment_id_info=342c209d-0a0c-4149-ac42-75ed863a2d18; _gcl_au=1.1.509566218.1639379580; _ga=GA1.2.2036572776.1639379581; _gid=GA1.2.251318869.1639379581; STORE_VISITOR=1; _clck=1yg66ys|1|ex8|0; _ju_dm=cookie; _ju_dn=1; _ju_dc=1d722071-5be4-11ec-9f18-cbc5ca27a912; SHOP_SESSION_TOKEN=20dc46blirnr614f7u88r353ur; fornax_anonymousId=c36e27fa-7a0f-4547-bd25-3f5d003cb4f8; XSRF-TOKEN=473a099babe808b4fe83ab47313788ad5df62931b064f7183916a32084c6f9ad; _hjSessionUser_912432=eyJpZCI6IjdmMGJkNjNkLTdkNDMtNTFhMy1hZmVjLTA0N2NlY2YxMjcyMSIsImNyZWF0ZWQiOjE2MzkzNzk1ODIyODMsImV4aXN0aW5nIjp0cnVlfQ==; tracker_device=47c8197b-629e-47e7-b8ca-bcf0f0b61573; _hjSession_912432=eyJpZCI6IjBkZWRlNzQ0LWUxYjQtNGFiOS1hZTQyLWUyMGVmNmExNGYyMSIsImNyZWF0ZWQiOjE2MzkzODI3NjQ5ODJ9; _hjIncludedInPageviewSample=1; _hjAbsoluteSessionInProgress=0; _hjIncludedInSessionSample=1; _sp_ses.3107=*; lastVisitedCategory=165; _ju_v=4.1_5.01; Shopper-Pref=BE144F003E633759A0D1841203AE6D9D8A43CF42-1639989857046-x%7B%22cur%22%3A%22USD%22%7D; _uetsid=1b32b3d05be411eca66b116e76deda47; _uetvid=1b32dc405be411ec9656974d7b93fd0f; _ju_pn=59; _clsk=vqjkeb|1639385434053|63|1|d.clarity.ms/collect; _sp_id.3107=4bb6dc451ac3257b.1639379595.2.1639385438.1639380705',
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
                response = requests.post('https://www.signalboosters.com/remote/v1/product-attributes/' + product_id,
                                         headers=headers, data=data)
                sku_json = json.loads(response.text)
                data_json = sku_json["data"]
                sku_info["current_price"] = str(data_json["price"]["without_tax"]["value"])
                if items["current_price"] != items["original_price"]:
                    sku_info["original_price"] = str(data_json["price"]["rrp_without_tax"]["value"])
                else:
                    sku_info["original_price"] = str(data_json["price"]["without_tax"]["value"])
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
