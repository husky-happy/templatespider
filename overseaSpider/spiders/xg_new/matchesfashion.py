# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from urllib import parse
from hashlib import md5
from pprint import pprint
from collections import defaultdict
from copy import deepcopy
from overseaSpider.util.utils import isLinux
import demjson
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'matchesfashion'


class MatchesfashionSpider(scrapy.Spider):
    name = website
    allowed_domains = ['matchesfashion.com']

    # start_urls = ['http://matchesfashion.com/']

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
        super(MatchesfashionSpider, self).__init__(**kwargs)
        setattr(self, 'author', "软猪")
        self.count = 0
        self.headers = {
            'authority': 'www.matchesfashion.com',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
            'sec-ch-ua-mobile': '?0',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': 'ab-user-id=14; _dy_c_exps=; fsm_uid=cf3ec459-7abe-c3b5-9608-dc225c0b0dbd; __tmbid=us-1625480576-1f38cc64ca2b496da1d90cd2cfa15dbf; _dycnst=dg; _gcl_au=1.1.427719884.1625480579; _dyid=4877399407385042304; _pxvid=f0da9ea1-dd7a-11eb-9f5b-27f0cfee29a6; _cs_c=0; _ga=GA1.2.1980838570.1625480583; _fbp=fb.1.1625480584766.578188240; _pin_unauth=dWlkPU5UTmxNek0wTldZdE16bGlZUzAwWVdNd0xUaGhOell0TWpBeE56UmpZVFUwWVdZNQ; rskxRunCookie=0; rCookie=mm866k8fb1vbwm4wc1xfekqqh68fs; _dyid_server=4877399407385042304; signed-up-for-updates=true; JSESSIONID=s4~C6046E6F195FEC729AEA119DC452AD0A; loggedIn=false; _pxhd=OVzMoBEZizssALhkgaAyYRFD8SA0QlOn4wE7kyZrJ5rl6oxp0g2y6QUSlBwC2JzKqPiCFaCzhV9gexfwHhVjcA==:K7bVbXEBTyQ0enSbFllu8PBpDxVuMx5BC9IMMk-DDrU72Yl23Fl/9fJUtM17kejFu35cmJqPHMsSaSQffMH1zVJkYh6Km03sxzpiXCmZPgI=; _dy_csc_ses=t; SESSION_TID=KRELK0WP7SDTD-L5KJ73; cb-enabled=enabled; notFirstVisit=true; cb-shown=true; fsm_sid=88004505-68e5-db28-99a1-20aea1e585de; AMCV_62C33A485B0EB69A0A495D19%40AdobeOrg=-1124106680%7CMCIDTS%7C18831%7CMCMID%7C60384746050663695234184171528043884843%7CMCAAMLH-1627543940%7C9%7CMCAAMB-1627543940%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1626946340s%7CNONE%7CvVersion%7C5.2.0; AMCVS_62C33A485B0EB69A0A495D19%40AdobeOrg=1; pxcts=f3962000-eabe-11eb-912d-e34337077002; _dyjsession=d9bbbcce5a158e023c33c1346caabc77; dy_fs_page=www.matchesfashion.com; _dy_geo=US.NA.US_.US__; _dy_df_geo=United%20States..; _gid=GA1.2.1434931268.1626939143; country=USA; billingCurrency=USD; language=en_US; saleRegion=US; sizeTaxonomy=""; gender=mens; defaultSizeTaxonomy=MENSSHOESUSSEARCH; _dycst=dk.w.c.ms.; _dy_ses_load_seq=32704%3A1626941152629; _dy_soct=1001485.1001871.1626941152; _dd_s=rum=0&expire=1626942052902; _cs_id=34fb5125-a9d4-a59a-a449-8851d4731869.1625480582.2.1626941154.1626939142.1.1659644582108.Lax.0; _cs_s=15.1.0.1626942954063; _dy_lu_ses=d9bbbcce5a158e023c33c1346caabc77%3A1626941154194; _dy_toffset=-2; sailthru_pageviews=14; _uetsid=f44d5c20eabe11ebad64916ec7b4af8e; _uetvid=fb0ed110dd7a11ebba9c815a6948e3a5; sailthru_content=7b90df1f6da5f8a612c3ae8c6f7518efb66f6d980cf726643bfee3d139d2111274ea7649b23a40bdf890e163c6f27656f9f5761332df3a1a717c5e665b659a92f42b0c007b34b900dd193136345b1ff157237ddb44f8ae0a1280771e15590e312b8495afad1d219d93423ae78e46e353a3aff1d739fc610862d89fa496c9e258; sailthru_visitor=3f30b293-427c-4615-9cae-6047b0a9d8d6; lastRskxRun=1626941157861; _px2=eyJ1IjoiYTJmYTMxNDAtZWFjMy0xMWViLTgxM2QtZjEwMThkMzkwMzJmIiwidiI6ImYwZGE5ZWExLWRkN2EtMTFlYi05ZjViLTI3ZjBjZmVlMjlhNiIsInQiOjE2MjY5NDIwOTU4MTcsImgiOiJiOGYxMzI2NTg5NjNiZTYyOGI2ZTliNWExNzg2ZmUzNDZmN2IwMWIwZmZmMmE3NDJjNDVkNjIxMmM1ZmE2YjgwIn0=; JSESSIONID=s6~EA86708A6BA1811AC69612A509714368; _pxhd=OVzMoBEZizssALhkgaAyYRFD8SA0QlOn4wE7kyZrJ5rl6oxp0g2y6QUSlBwC2JzKqPiCFaCzhV9gexfwHhVjcA==:K7bVbXEBTyQ0enSbFllu8PBpDxVuMx5BC9IMMk-DDrU72Yl23Fl/9fJUtM17kejFu35cmJqPHMsSaSQffMH1zVJkYh6Km03sxzpiXCmZPgI=; ab-user-id=21; billingCurrency=USD; country=USA; defaultSizeTaxonomy=WOMENSSHOESUSSEARCH; language=en_US; loggedIn=false; saleRegion=US'
        }

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,

        # 'MONGODB_DB': 'fashionspider',
        # 'MONGODB_COLLECTION': 'fashions_pider',

        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'INFO',
        'COOKIES_ENABLED': False,
        # 'HTTPCACHE_ALWAYS_STORE': True,
        'HTTPCACHE_ENABLED': True,
        # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60,  # 秒
        # 'HTTPCACHE_DIR': "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache",
        'DOWNLOADER_MIDDLEWARES': {
            # 'overseaSpider.middlewares.OverseaspiderDownloaderMiddleware': 543,
            'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.DummyPolicy',
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.RFC2616Policy',
        # 'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):

        url_list = ["https://www.matchesfashion.com/us/api/designers/mens/az"]
        for url in url_list:
            yield scrapy.Request(
                url=url,
                # dont_filter=True,
                headers=self.headers,

            )

    def parse(self, response):
        """主页"""

        url = response.url
        # print("*"*100)

        # print("*"*100)
        brand_json_data = response.text
        brand_json_list = json.loads(brand_json_data)
        brand_url_list = []
        for index in brand_json_list:
            if "designers" in index:
                designer_list = index["designers"]
                for index2 in designer_list:
                    if "url" in index2:
                        brand_url_list.append(index2["url"])

        brand_url_list = list(set(brand_url_list))

        # print(len(brand_url_list))

        for url in brand_url_list:
            url = response.urljoin(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                headers=self.headers,
                # dont_filter=True,
            )

    def parse_list(self, response):
        """商品列表页"""

        detail_url_list = response.xpath(
            '//ul[contains(@class,"lister")]/li[contains(@class,"item")]//div[contains(@class,"productView")]/a/@href').getall()

        if detail_url_list:

            # print(detail_url_list)
            # print(f"当前商品列表页有{len(detail_url_list)}条数据")

            for detail_url in detail_url_list:
                detail_url = response.urljoin(detail_url)
                # print("详情页url:"+detail_url)
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    headers=self.headers,
                )

            next_page_url = response.xpath('//li[@class="next"]/a/@href').get().strip() if response.xpath(
                '//li[@class="next"]/a/@href') else None

            if next_page_url:
                next_page_url = response.urljoin(next_page_url)
                print("下一页:" + next_page_url)
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_list,
                    headers=self.headers,
                )

    def filter_text(self, input_text):
        input_text = re.sub(r'[\t\n\r\f\v]', ' ', input_text)
        input_text = re.sub(r'<.*?>', ' ', input_text)
        filter_list = [u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000-', u'\u200a',
                       u'\u2028', u'\u2029', u'\u202f', u'\u205f', u'\u3000', u'\xA0', u'\u180E',
                       u'\u200A', u'\u202F', u'\u205F', u'\x93', u'\x94', u'\x95', u'\x96']
        for index in filter_list:
            input_text = input_text.replace(index, "").strip()
        return input_text

    def parse_detail(self, response):
        """详情页"""
        # print("*"*100)
        # print("详情页了了了了",response.url)
        items = ShopItem()

        html_json_data = response.xpath('//script[@type="application/json"]//text()').get()
        json_data = json.loads(html_json_data)
        json_data = defaultdict(lambda: None, json_data)

        in_stock = response.xpath('//button[contains(@data-testid,"add-to-bag")]').get()

        if in_stock:

            product_json_data = json_data["props"]["pageProps"]["product"]

            items["url"] = response.url

            if "basicInfo" in product_json_data:
                items["name"] = product_json_data["basicInfo"]["name"].strip() if "name" in product_json_data[
                    "basicInfo"] else None
                items["brand"] = product_json_data["basicInfo"][
                    "designerName"].strip() if "designerName" in product_json_data else product_json_data["basicInfo"][
                    "designerNameEn"]

                flag = False
                if "categories" in product_json_data:
                    if product_json_data["categories"][-1]:
                        if "url" in product_json_data["categories"][-1]:
                            items["detail_cat"] = product_json_data["categories"][-1]["url"].replace('us', '').replace(
                                '//', '')
                            items["cat"] = items["detail_cat"].split("/")[-1]
                            flag = True
                if flag == False:
                    detail_cat_list = response.xpath('//nav[contains(@class,"breadcrumb")]/ol/li/a//text()').getall()
                    if detail_cat_list:
                        detail_cat_list = [cat.replace('\n', '').strip() for cat in detail_cat_list]
                        items["detail_cat"] = ''.join(detail_cat_list)
                        items["cat"] = detail_cat_list[-1]

                if "editorial" in product_json_data:
                    if "description" in product_json_data["editorial"]:
                        items["description"] = self.filter_text(product_json_data["editorial"]["description"])
                    if "detailBullets" in product_json_data["editorial"]:
                        attribute_list = product_json_data["editorial"]["detailBullets"]
                        if attribute_list:
                            attribute_list = [self.filter_text(index) for index in attribute_list]
                            items["attributes"] = attribute_list

                if "pricing" in product_json_data:
                    if "rrp" in product_json_data["pricing"]:
                        if "displayValue" in product_json_data["pricing"]["rrp"]:
                            items["original_price"] = product_json_data["pricing"]["rrp"]["displayValue"]
                        else:
                            items["original_price"] = '$' + str(
                                product_json_data["pricing"]["rrp"]["amount"] / product_json_data["pricing"]["rrp"][
                                    "divisor"]).strip()

                    items["current_price"] = product_json_data["pricing"]["billing"]["displayValue"] if \
                    product_json_data["pricing"]["billing"]["displayValue"] else '$' + str(
                        product_json_data["pricing"]["billing"]["amount"] / product_json_data["pricing"]["billing"][
                            "divisor"]).strip()

                    if "original_price" not in items:
                        items["original_price"] = items["current_price"]

                items["source"] = website

                img_list = []
                if "gallery" in product_json_data:
                    img_json_data = product_json_data["gallery"]
                    if "images" in img_json_data:
                        for img_json in img_json_data["images"]:
                            if "sequence" in img_json and "template" in img_json:
                                sequence_list = img_json["sequence"]
                                for i in sequence_list:
                                    img_list.append(
                                        img_json["template"].replace('{WIDTH}', '1000').replace('{SEQUENCE}', i))
                if len(img_list) < 1:
                    img_list = response.xpath('//img[contains(@class,"img")]/@src').getall()
                img_list = ['https:' + img.strip() for img in img_list]

                items["images"] = img_list

                sku_list = list()
                if "sizes" in product_json_data:
                    size_json_list = product_json_data["sizes"]
                    for size in size_json_list:
                        if size["stock"] != 'outOfStock':
                            sku_info = SkuItem()
                            sku_att = SkuAttributesItem()

                            sku_info["sku"] = size["code"].strip() if "code" in size else None
                            sku_att["size"] = size["displayName"].strip() if "displayName" in size else None
                            sku_att["colour"] = product_json_data["basicInfo"]["colour"].strip() if "colour" in \
                                                                                                    product_json_data[
                                                                                                        "basicInfo"] else None
                            sku_info["imgs"] = items["images"]
                            sku_info["attributes"] = sku_att

                            sku_info["current_price"] = items["current_price"]
                            sku_info["original_price"] = items["original_price"]
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

                print(items)
                yield items
