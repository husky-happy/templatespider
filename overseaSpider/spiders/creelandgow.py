# -*- coding: utf-8 -*-
import itertools
import re
import json
import time
import scrapy
import requests
from hashlib import md5
from bs4 import BeautifulSoup
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'creelandgow'


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
    allowed_domains = ['creelandgow.com']
    start_urls = ['https://creelandgow.com/']

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
        category_urls = response.xpath("//ul[@id='header-menu-desktop']/li[position()<7]/a/@href").getall()
        category_cate = response.xpath("//ul[@id='header-menu-desktop']/li[position()<7]/a/text()").getall()
        for c in range(len(category_urls)):
            yield scrapy.Request(url=category_urls[c], callback=self.parse_list, meta={"cat":category_cate[c]})

    def parse_list(self,response):
        cate= response.meta.get("cat")
        detail_url_list = response.xpath("//div[@class='row bloc-item-product']/div/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail, meta={"cat":cate})
        next_page_url = response.xpath("//link[@rel='next']/@href").get()
        # print(next_page_url)
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list, meta={"cat":cate})

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        cate = response.meta.get("cat")
        price = response.xpath("//div[@class='detail-content-product']//bdi/text()").get()
        price = price.replace(',','')
        items["original_price"] = price
        items["current_price"] = price

        name = response.xpath("//h1/text()").get()
        items["name"] = name

        cat_list = ['Home',cate]
        if cat_list:
            cat_list = [cat.strip() for cat in cat_list if cat.strip()]
            items["cat"] = cat_list[-1]
            items["detail_cat"] = '/'.join(cat_list)

        description = response.xpath("//div[@class='info-detail-product']").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list_tmp = response.xpath("//img[@class='img-responsive']/@src").getall()
        images_list = []
        for i in range(len(images_list_tmp)):
            if(i<=1):
                images_list.append(images_list_tmp[i])
        items["images"] = images_list
        items['brand'] = ''
        sku_string = response.xpath("//form[@class='variations_form cart']/@data-product_variations").get()

        if not sku_string:
            items["sku_list"] = []
        else:
            sku_json = json.loads(sku_string)
            opt_name = []
            if 'attribute_pa_size' in sku_json[0]['attributes']:
                opt_name.append('size')
            elif 'attribute_pa_name_variation' in sku_json[0]['attributes']:
                opt_name.append('other')
            else:
                return
            opt_value = []
            opt_length = len(opt_name)
            size_price = dict()
            for i in range(opt_length):
                value_temp = []
                if opt_name[i]=='size':
                    for j in sku_json:
                        s = j['attributes']['attribute_pa_size']
                        s=s.replace("-",'.')
                        s=s.replace("%e2%80%b3",'')
                        value_temp.append(s)
                        size_price[s]=str(j['display_price'])
                    opt_value.append(value_temp)
                else:
                    for j in sku_json:
                        value_temp.append(j['attributes']['attribute_pa_name_variation'])
                        size_price[j['attributes']['attribute_pa_name_variation']]=str(j['display_price'])
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

            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()

                for attr in attrs.items():
                    if attr[0] == 'size':
                        sku_attr["size"] = attr[1]
                        sku_info["current_price"] = size_price[sku_attr["size"]]
                        sku_info["original_price"] = size_price[sku_attr["size"]]
                    else:
                        other_temp[attr[0]] = attr[1]
                        sku_info["current_price"] = size_price[attr[1]]
                        sku_info["original_price"] = size_price[attr[1]]
                if len(other_temp):
                    sku_attr["other"] = other_temp

                sku_info["attributes"] = sku_attr

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
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        # print(items)
        yield items
