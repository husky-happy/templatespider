# -*- coding: utf-8 -*-
import html
import re
import itertools
import json
import time
import scrapy
import requests
from hashlib import md5
from overseaSpider.util.scriptdetection import detection_main
from overseaSpider.util.item_check import check_item
from overseaSpider.util.utils import isLinux
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'wheatridgecyclery'
# 全流程解析脚本

class wheatridgecyclery(scrapy.Spider):
    name = website
    # allowed_domains = ['wheatridgecyclery']
    start_urls = 'https://www.wheatridgecyclery.com/'


    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"] = 6
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(wheatridgecyclery, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', "流冰")

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': True,
         # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        #'DOWNLOAD_HANDLERS': {
        #'https': 'scrapy.core.downloader.handlers.http2.H2DownloadHandler',
        #},
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def clear_price(self,org_price,cur_price,Symbol='$'):
        """价格处理"""
        if not org_price and not cur_price:
            return None, None
        org_price = org_price.split('-')[0] if org_price and '-' in org_price else org_price
        cur_price = cur_price.split('-')[0] if cur_price and '-' in cur_price else cur_price
        if org_price:
            org_price = str(org_price).replace(Symbol, '').replace(' ', '').replace(',', '.').strip()
        if cur_price:
            cur_price = str(cur_price).replace(Symbol, '').replace(' ', '').replace(',', '.').strip()
        org_price = org_price if org_price and org_price != '' else cur_price
        cur_price = cur_price if cur_price and cur_price != '' else org_price
        if org_price.count(".") > 1:
            org_price =list(org_price)
            org_price.remove('.')
            org_price = ''.join(org_price)
        if cur_price.count(".") > 1:
            cur_price =list(cur_price)
            cur_price.remove('.')
            cur_price = ''.join(cur_price)
        return org_price, cur_price

    def product_dict(self,**kwargs):
        # 字典值列表笛卡尔积
        keys = kwargs.keys()
        vals = kwargs.values()
        for instance in itertools.product(*vals):
            yield dict(zip(keys, instance))

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
            u'\u3000', u'\xA0', u'\u180E', u'\u200A', u'\u202F', u'\u205F',u'\u200b',u'\x9d','\t', '\n', '\r', '\f', '\v',
        ]
        for f_char in filter_char_list:
            text = text.replace(f_char, '')
        text = re.sub(' +', ' ', text).strip()
        return text

    def remove_space_and_filter(self,l):
        # 洗列表文本
        new_l = []
        for i,j in enumerate(l):
            k = self.filter_html_label(j)
            if k == '':
                continue
            # if not k.strip().endswith('.') and not k.strip().endswith(':') and not k.strip().endswith(',') \
            #         and not k.strip().endswith('?') and not k.strip().endswith('!'):
            #     k = k+'.'
            new_l.append(k)
        return new_l

    def start_requests(self):
        url_list = [
            "https://www.wheatridgecyclery.com/",
        ]
        for url in url_list:
           print(url)
           yield scrapy.Request(
              url=url,
           )

    def parse(self, response):
        url_list = response.xpath("//ul[@class='link-list']/li/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//div[@class='seProductTitle']/a/@href").getall()
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )
        next_page_url = response.xpath("//a[@title='Next page']/@href").getall()
        if next_page_url:
            next_page_url = next_page_url[0]
            next_page_url = response.urljoin(next_page_url)
            print("下一页:"+next_page_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list,
            )

    def get_attributes(self,response):
        # 处理attributes
        attributes_l = list()
        attr_key = response.xpath("//table[@class='table seProductSpecTable']//tr//th/text()").getall()
        attr_key = self.remove_space_and_filter(attr_key)
        org_attr_value = response.xpath("//table[@class='table seProductSpecTable']//tr//td")
        attr_value = []
        for i, org_attr in enumerate(org_attr_value):
            attr_list = org_attr.xpath(".//text()").getall()
            attr_list = self.remove_space_and_filter(attr_list)
            if len(attr_list) > 0:
                attr_v = ''.join(attr_list)
                attr_value.append(attr_v)
            else:
                if i < len(attr_key):
                    del attr_key[i]
                    continue
        for i in range(len(attr_key)):
            attributes_l.append(attr_key[i] + ":" + attr_value[i])
        return attributes_l

    def parse_detail(self, response):
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        # price = re.findall("", response.text)[0]
        original_price = response.xpath("//div[@id='OriginalPrice']/text()").get()
        current_price = response.xpath("//div[@id='SpecialPrice']/text()").get()
        if not current_price:
            current_price = response.xpath("//div[@id='RegularPrice']//text()").get()
        items["original_price"],items["current_price"] = self.clear_price(original_price,current_price)
        if not items["current_price"]:
            return
        items["brand"] = response.xpath("//span[@class='seProductBrandName']/text()").get()
        if not items["brand"]:
            items["brand"] = ''
        items["name"] = response.xpath("//meta[@property='og:title']/@content").get()
        items["attributes"] = self.get_attributes(response)
        # abt = response.xpath("").getall()
        # abt = self.remove_space_and_filter(abt)
        # items["about"] = ' '.join(abt)
        des = response.xpath("//p[@class='seProductPrimaryDescription']//text()").getall()
        des = self.remove_space_and_filter(des)
        items["description"] = ' '.join(des)
        #items["care"] = response.xpath("").get()
        #items["sales"] = response.xpath("").get()
        source = self.start_urls.split("www.")[-1].split("//")[-1].replace('/','')
        items["source"] = source
        images_list = response.xpath("//li[@class='seitemimagecarousel-item touchcarousel-item']/img/@src").getall()
        if len(images_list) == 0:
            images_list = response.xpath("//img[@class='img-responsive seLargeImage']/@src").getall()
        images_list = [i.replace('micro', 'zoom') for i in images_list]
        images_list = [response.urljoin(i) for i in images_list]
        items["images"] = images_list

        Breadcrumb_list = response.xpath("//ol[@class='breadcrumb seProductBreadcrumb']//li//span//text()").getall()
        Breadcrumb_list = self.remove_space_and_filter(Breadcrumb_list)
        items["cat"] = Breadcrumb_list[-1]
        items["detail_cat"] = '/'.join(Breadcrumb_list)

        sku_label = response.xpath("//label[@class='seItemVariationLabel']/text()").getall()
        sku_label = self.remove_space_and_filter(sku_label)
        sku_list = list()
        org_sku_list = []
        sku_variant = response.xpath("//div[@class='seProductPartNumbersTableWrapper']//tbody//tr")
        script_list = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        for script in script_list:
            json_data = json.loads(script)
            if 'offers' in json_data.keys():
                org_sku_list = json_data["offers"]
                break
        if len(sku_variant) > 1:
            for sku in sku_variant:
                sku_item = SkuItem()
                attributes = SkuAttributesItem()
                other = dict()
                sku_id = sku.xpath("./td[@data-th='UPC']/text()").get().strip()
                sku_name = sku.xpath("./td[@data-th='Option']/text()").get().strip()
                sku_name_list = sku_name.split(" / ")
                if len(sku_name_list) > len(sku_label):
                    sku_name_list = sku_name_list[1:]
                for i, j in enumerate(sku_name_list):
                    s_l = sku_label[i]
                    if 'ize' in s_l:
                        attributes["size"] = j.strip()
                    elif 'olo' in s_l:
                        attributes['colour'] = j.strip()
                    else:
                        other[s_l] = j
                sku_item["sku"] = sku_id
                sku_price = sku_url = ''
                for gtin in org_sku_list:
                    if sku_id == gtin["gtin"]:
                        sku_price = gtin["price"]
                        sku_url = gtin["url"]
                sku_item["url"] = sku_url
                sku_item["original_price"] = sku_item["current_price"] = sku_price
                sku_item["url"] = response.url
                try:
                    if attributes['colour']:
                        sku_imgs = response.xpath(
                            "//li[@class='seitemimagecarousel-item touchcarousel-item']/img[contains(@title,'{}')]/@src"
                                .format(attributes['colour'])).getall()
                        for i, j in enumerate(sku_imgs):
                            sku_imgs[i] = j.replace('micro', 'zoom')
                        if len(sku_imgs) > 0:
                            sku_item["imgs"] = sku_imgs
                except:
                    pass
                if len(other)>0:
                    attributes["other"] = other
                sku_item["attributes"] = attributes
                sku_list.append(sku_item)

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

        yield items
        # print(items)
        # check_item(items)
        # detection_main(items=items, website=website, num=self.settings["CLOSESPIDER_ITEMCOUNT"], skulist=True,
        #                 skulist_attributes=True)
