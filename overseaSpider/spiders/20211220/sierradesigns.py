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

# !/usr/bin/env python
# -*- coding: UTF-8 -*-
'''=================================================
@Project -> File   ：templatespider -> sierradesigns
@IDE    ：PyCharm
@Author ：Mr. Husky
@Date   ：2021/12/21 14:22
@Desc   ：
=================================================='''

website = 'sierradesigns'
website_url = 'https://sierradesigns.com'

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
    allowed_domains = ['sierradesigns.com']
    start_urls = ['https://sierradesigns.com/']

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
        category_urls = response.xpath("//li[@class='navPage-subMenu-action navPages-action-depth-max']/a/@href").getall()
        for category_url in category_urls:
            category_url = website_url + category_url
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//li[@class='product']/article/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_new = response.xpath("//div[@class='productView-product']//span[contains(@class,'price price--withoutTax')]/text()").get()
        price_new = price_new.split("-")[0]
        price_new = self.price_fliter(price_new)
        price_old = response.xpath("//div[@class='productView-product']//div[not(@style)]/span[contains(@class,'price price--rrp')]/text()").get()
        if price_old:
            price_old = self.price_fliter(price_old)
            items["original_price"] = price_old
        else:
            items["original_price"] = price_new
        items["current_price"] = price_new

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = response.xpath("//ul[@class='breadcrumbs']/li/a//text()").getall()
        cat_list.append(name)
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='default-description']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = 'sierradesigns.com'

        # attr1_list = response.xpath("//div[@class='single-car-data']/table//tr/td[1]/text()").getall()
        # attr2_list = response.xpath("//div[@class='single-car-data']/table//tr/td[2]/text()").getall()
        # attribute = []
        # for a in range(len(attr1_list)):
        #     attribute.append(attr1_list[a] + ":" + attr2_list[a])
        # items["attributes"] = attribute

        images_list = response.xpath("//div[@class='productView-thumbnail']/a/@href").getall()
        items["images"] = images_list
        items["brand"] = 'Sierra Designs'

        opt_name_tmp = response.xpath("//div[@class='productView-options']/form/div[@data-product-option-change]/div/label[@class='form-label form-label--alternate form-label--inlineSmall']/text()").getall()
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
                value_temp = response.xpath("//div[@class='productView-options']/form/div[@data-product-option-change]/div["+str(i+1)+"]/label[@class='form-option']/span/text()").getall()
                if not value_temp:
                    value_temp = response.xpath("//div[@class='productView-options']/form/div[@data-product-option-change]/div["+str(i+1)+"]/label[@class='form-option']/span/@title").getall()
                value_value = response.xpath("//div[@class='productView-options']/form/div[@data-product-option-change]/div["+str(i+1)+"]/input/@value").getall()
                for v in range(len(value_value)):
                    value_dict[value_temp[v]] = value_value[v]
                attr_name = response.xpath(
                    "//div[@class='productView-options']/form/div[@data-product-option-change]/div["+str(i+1)+"]/input/@name").get()
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
                'authority': 'sierradesigns.com',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'stencil-config': '{}',
                'x-xsrf-token': '42488250d4bb32b6952cbe010a0e8c1de2a323ce4ac55f299c3ddb3e4d9fc6df, 42488250d4bb32b6952cbe010a0e8c1de2a323ce4ac55f299c3ddb3e4d9fc6df',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'accept': '*/*',
                'x-requested-with': 'XMLHttpRequest',
                'stencil-options': '{"render_with":"products/bulk-discount-rates"}',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://sierradesigns.com',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
                'cookie': 'fornax_anonymousId=6583af5b-0cb5-4845-b07a-ff1324e092e6; ajs_user_id=null; ajs_group_id=null; ajs_anonymous_id=%227b49af11-b699-4cd0-8ad9-c7cf7658da61%22; _gcl_au=1.1.569035954.1638266557; ku1-vid=e8b8f2a1-c400-e752-abec-132106083715; _shg_user_id=3d1c36b4-c2a4-4569-836f-ebf336eec2ec; _ga=GA1.2.1201201297.1638266557; ssUserId=a3257b20-a64d-4aa2-89bb-da6d5a222892; _pin_unauth=dWlkPVpEWXhNak0xTkRRdE5ESXlZeTAwTUdZeExXRTFZV0l0TlRka1lqbGhaV1JrWTJGaw; hw_uuid=5f3407e4968949ba942490f7e8fe5ed5; _isuid=V3-1FE6FE0A-0E0F-402D-8692-FEF06DE953BD; candid_userid=35637d12-21be-4438-b02c-34c27dd24cda; __kla_id=eyIkcmVmZXJyZXIiOnsidHMiOjE2MzgyNjY1NTcsInZhbHVlIjoiaHR0cDovLzIwLjgxLjExNC4yMDg6ODAwMC8iLCJmaXJzdF9wYWdlIjoiaHR0cHM6Ly9zaWVycmFkZXNpZ25zLmNvbS8ifSwiJGxhc3RfcmVmZXJyZXIiOnsidHMiOjE2Mzg0OTgwODMsInZhbHVlIjoiaHR0cDovLzIwLjgxLjExNC4yMDg6ODAwMC8iLCJmaXJzdF9wYWdlIjoiaHR0cHM6Ly9zaWVycmFkZXNpZ25zLmNvbS8ifX0=; SHOP_SESSION_TOKEN=b76fk1ajq846b1jacnmsg96h28; _ks_scriptVersion=308; XSRF-TOKEN=42488250d4bb32b6952cbe010a0e8c1de2a323ce4ac55f299c3ddb3e4d9fc6df; ku1-sid=HXZDfVlsXDTUQGWDpVNoB; _clck=1jiyo6k|1|exg|0; _shg_session_id=48559e38-4135-4a2f-af16-0cd3bf0ab7fd; _gid=GA1.2.1639089079.1640067401; STORE_VISITOR=1; _ks_scriptVersionChecked=true; __insp_wid=1579265263; __insp_nv=true; __insp_targlpt=U2llcnJhIERlc2lnbnM6IEJhY2twYWNraW5nIFRlbnRzLCBTbGVlcGluZyBCYWdzLCBPdXRkb29yIENsb3RoaW5n; __insp_targlpu=aHR0cHM6Ly9zaWVycmFkZXNpZ25zLmNvbS8%3D; __insp_norec_sess=true; _ce.s=v11.rlc~1640067403442~v~83bf571c0bc6c2fc28e3584e9b6401957efb94e3~vpv~0~ir~1~gtrk.la~kwlxn9kb; _ks_countryCodeFromIP=HK; _ks_userCountryUnit=1; lastVisitedCategory=642; ssViewedProducts=2551519%2C70603820%2C77610921%2C77610721%2C22595120%2C4593320%2C40157621%2C22595520%2C40153417%2C40147018; ssSessionIdNamespace=82e36b5f-e9d4-4e9b-b07d-e89174492238; _uetsid=8f86ef80622511ecaa8dd7a56bf27884; _uetvid=a52c833051c411ec9613c98aa9be1d4e; __insp_slim=1640067721965; kiwi-sizing-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzaWQiOiI0ODliNmZmMS04MjM3LTQ2MmQtYWY5NC0yOWNmNjcyY2I5YjkiLCJpYXQiOjE2NDAwNjc3MjIsImV4cCI6MTY0MDA3MTMyMn0.zmDZ0uXnJtvZ6NBBl0Ta1Ev9CqEJZOuWg6SCrVwjlok; avmws=1.159474474461a5f6c172a71310203553.92383369.1640067401.1640067724.21.1342657573; _clsk=ar636k|1640067938897|21|1|e.clarity.ms/collect; Shopper-Pref=D93CBB668F8F324C804F42D8D70847A431D30D59-1640672741389-x%7B%22cur%22%3A%22USD%22%7D; _gali=attribute_rectangle__2825_3060',
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
                    elif attr[0].find("Color") != -1:
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp
                response = requests.post('https://sierradesigns.com/remote/v1/product-attributes/'+product_id, headers=headers, data=data)
                sku_json = json.loads(response.text)
                data_json = sku_json["data"]
                sku_info["current_price"] = str(data_json["price"]["without_tax"]["value"])
                if "rrp_without_tax" in data_json["price"]:
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
