# -*- coding: utf-8 -*-
import itertools
import re
import json
import time
import scrapy
import requests
from hashlib import md5

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.utils import isLinux

website = 'nunido'


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
    allowed_domains = ['nunido.de']
    start_urls = ['https://www.nunido.de/']

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
        setattr(self, 'author', "叶石")

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
        category_urls = response.xpath("//a[@role='menuitem']/@href").getall()
        for category_url in category_urls:
            yield scrapy.Request(url=category_url, callback=self.parse_list)

    def parse_list(self, response):
        """商品列表页"""
        detail_url_list = response.xpath("//div[@class='productListItem']/a/@href").getall()
        for detail_url in detail_url_list:
            yield scrapy.Request(url=detail_url, callback=self.parse_detail)
        next_page_url = response.xpath("//a[@class='next']/@href").get()
        if next_page_url:
            yield scrapy.Request(url=next_page_url, callback=self.parse_list)

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url

        price_now = response.xpath("//span[@id='productPrice']/text()").get()
        items["current_price"] = price_now.replace(',', '.').strip()
        if items["current_price"].count('.') == 2:
            pos = items["current_price"].find('.')
            items["current_price"] = items["current_price"][:pos] + items["current_price"][pos + 1:]
        price_old = response.xpath("//span[@id='oldPrice']/text()").get()
        if price_old:
            items["original_price"] = price_old.replace(',', '.').strip()
            if items["original_price"].count('.') == 2:
                pos = items["original_price"].find('.')
                items["original_price"] = items["original_price"][:pos] + items["original_price"][pos + 1:]
        else:
            items["original_price"] = items["current_price"]

        name = response.xpath("//h1[@id='productTitle']/span/text()").get()
        items["name"] = name
        items["brand"] = response.xpath("//div[@itemprop='brand']/meta/@content").get()
        # cat_list = response.xpath('//ul[@class="breadcrumbs"]/li/a/text()').getall()
        # if cat_list:
        #     cat_list = [cat.strip() for cat in cat_list if cat.strip()]
        #     items["cat"] = cat_list[-1]
        #     items["detail_cat"] = '/'.join(cat_list)

        items["cat"] = ''
        items["detail_cat"] = ''

        description = response.xpath("//div[@class='productDescription']/text()").getall()
        items["description"] = self.filter_text(self.filter_html_label(''.join(description)))
        items["source"] = website

        images_list = response.xpath("//li[@class='col-lg-10 col-md-10 col-xs-3']/a/@href").getall()
        items["images"] = images_list

        opt_name = response.xpath("//div[@class='variantSelectBoxLabel pull-left text-left']/text()").getall()
        if not opt_name:
            items["sku_list"] = []
        else:
            opt_name = [name.replace(':', '').strip() for name in opt_name if name.strip()]
            opt_value = []
            # print(opt_name)
            opt_length = len(opt_name)
            for i in range(opt_length):
                value_temp = response.xpath("//div[@itemscope='itemscope']/div/div/div[" + str(i+1) +"]/div/select/option[not(contains(@value,-1))]/text()").getall()
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

            sku_list = list()
            for attrs in attrs_list:
                sku_info = SkuItem()
                sku_attr = SkuAttributesItem()
                other_temp = dict()

                for attr in attrs.items():
                    if attr[0] == 'Größe':
                        sku_attr["size"] = attr[1]
                    elif attr[0] == 'Farbe':
                        sku_attr["colour"] = attr[1]
                    else:
                        other_temp[attr[0]] = attr[1]
                if len(other_temp):
                    sku_attr["other"] = other_temp

                sku_info["current_price"] = items["current_price"]
                sku_info["original_price"] = items["original_price"]
                sku_info["url"] = items["url"]
                sku_info["attributes"] = sku_attr
                img_url = "https://d2gik7xihfa6t2.cloudfront.net/master/product/"
                productid = response.xpath("//input[@name='nu[articlenr]']/@value").get()
                img_list = list()
                if '-' in productid:
                    productid = productid[0:productid.find('-')]
                    for i in range(1000):
                        Img_url = img_url + str(i+1) + "/" + productid + "-" +str(attrs_list.index(attrs)+1) + "_" + str(i+1) + ".jpg"
                        if str(requests.get(Img_url)) == "<Response [200]>":
                            img_list.append(Img_url)
                        else:
                            break;
                else:
                    for i in range(1000):
                        Img_url = img_url + str(i+1) + "/" + productid + "-" +str(attrs_list.index(attrs)+1) + "_" + str(i+1) + ".jpg"
                    if str(requests.get(Img_url)) == "<Response [200]>":
                        img_list.append(Img_url)
                    else:
                        break;
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
        # detection_main(items=items, website=website, num=10, skulist=True, skulist_attributes=True)
        print(items)
        yield items
