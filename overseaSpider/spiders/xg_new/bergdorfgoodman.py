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
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

website = 'bergdorfgoodman'


class BergdorfgoodmanSpider(scrapy.Spider):
    name = website
    allowed_domains = ['bergdorfgoodman.com']

    # start_urls = ['http://bergdorfgoodman.com/']

    @classmethod
    def update_settings(cls, settings):
        settings.setdict(
            getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {},
            priority='spider')

    def __init__(self, **kwargs):
        super(BergdorfgoodmanSpider, self).__init__(**kwargs)
        setattr(self, 'author', "软猪")
        self.headers = {
            # 'user-agent': 'PostmanRuntime/7.28.2',
            'authority': 'www.bergdorfgoodman.com',
            'cookie': 'TLTSID=EDBAF68CE9C510E9D1D9921F6DE1A93B; TLTUID=EDBAF68CE9C510E9D1D9921F6DE1A93B; JSESSIONID=hM0VgrkernOcFg63tmlbcPQFTyACDYFeNamZ8TFp.jsession; tms_data="{DT-2017.03}a3HwxssoiZzaMm5Pj2Bv6L13Gv8Ad/WZkJm2zLBiJ21ld4dfj9JnVCkhgm80R6HP7xq2mB+8hifNNcO91uyLeEFeMZtOQA406+Ht/s9AE+TfcYb/sMCrG5GtCWrOFhGcgoN5MKuLYDMlj6mQ0OjfPW1iVtMbd9Hi4Mk+yx4yZIi+wIEacND2v0yTe3M4NNS9SFFpjlsimIJzzKJyv9euiS7OkVBY+GUZF+ecU+kOb0bDV95v1JXbEap0WdnnZKEWr1bSVdLtV3YL+wJ35sjOS3Jon/EvBYTSJNYqcXMGjZtDDYYaL89+JdL7JpIKrmmRshJZi/ScaaRXXVL4yctoNrO743/x7UlvBPuoDUtTizU4kmkms2yRa4ls+pmS+Sl/dICbyH0ULzWe1TwUutTMkTiZQDhoFs2ju/fPGKxNvPevWTDX/yHg4qfwkDQ+IiOC3MNbpm4ZUdKZ4DyWzdy1BQfwtpEgBXJC/J23yoLJkLc87s3pecRmzBRk6sGBCCUtJZ+QRNulKPsGHStn2Z/g0VXsYjSn0Ex7uWzt8TfhE1OqdcCg2iP/iKqMSd/H11i+xIN0LxrkyzcneLN/46/gDU2hhZ0I3BHoZ4FG5fEYN/mHkMO/aPXYr1iaNO3QzJOEa4MZGFQzku8qOuYQHtZfCZ+h0N8LauKGohom0kidw4MzOz3k4eb7x/r3+L0mO6V2WKMtrlCMxpzVvr0YAvYICsKi8ag80EH9RXZ8KuaFRPi51xt415JH1zVDRd7reb37XAjhrrw1iyO8RFZTyy6NGA49kcyt5qqEtLnNF8HBP5wEY5ZmUdX/IhTUjckIBZ1sw2AQSUsoJmJle2TXB+0SLKXPpQMuapwqsGg6B2sKOB6iz4omj8kVw23zSEZ60E9UpRpQ/5ORQ2U75a/o2uzzGARv8jm+3JKuyzaeXIDU+iwQAO/226oO/8iYqEZPGX17f5m4Y0xZU1CYaVphIJtO4w=="; WID=7250953134; DYN_USER_ID=7250953134; DYN_USER_CONFIRM=e455b5a44010d84bb35453961a2f85c3; W2A=2282553354.57185.0000; _cplid=162683218716589; _optuid=1626832187165850; account=DT4; rxVisitor=16268321874816ONOAR11SPUML52E1PPCQ6BNADDMACIK; revisitUser=true; pxcts=f0ce8eb0-e9c5-11eb-b0a0-f98109fc6dbb; AMCVS_5E85123F5245B3520A490D45%40AdobeOrg=1; _evga_5944=7250953134.; _gcl_au=1.1.1551747491.1626832194; s_cc=true; dtCookie=10$C3EF54748BA8006172665FFB0F2BADD4|68bd3ff149c8f751|1; CChipCookie=2113994762.49245.0000; _ga=GA1.2.90223943.1626832197; _gid=GA1.2.868354105.1626832197; _fbp=fb.1.1626832199760.435277864; __qca=P0-1793895369-1626832198043; _pxvid=0ab819f7-e9c6-11eb-83f7-0242ac120009; _pxhd=j6NRvCJn1NrOozmWc-KHCBSeSsNjSvK4QNFcqdkIem6B-VvJcdiyJ5omX6AmbdacMr2K8EGeYUsVrpXpGJpR6A==:kG/yJmlFztXrV3sdSqJszSKOxejiCz7EURl0B-s1Ki5h-qCrguOiIITTgZHjjbx6TsFBj9mBSUblsptwI-BSHK8GGKzPMu9jMl/yEtBSHSU=; _optanalytics=; QuantumMetricUserID=a2e4ef9a5e80c42bddf6c908f6aeb0a3; QuantumMetricSessionID=fe7fa79f6d62e8e67c2fdb10656e4b9f; dtSa=-; pt_ck=silo; s_vnum=1627747200021%26vn%3D4; s_invisit=true; s_sq=%5B%5BB%5D%5D; xyz_cr_1049_et_111==NaN&cr=1049&et=111; utag_main=v_id:017ac6c13f45004377ebe610b88003073002006b0087e$_sn:4$_ss:0$_st:1626858101910$vapi_domain:bergdorfgoodman.com$_prevpage:Designers%3Bexp-1626859902001$ses_id:1626856230345%3Bexp-session$_pn:3%3Bexp-session; productnum=7; _uetsid=f4680c60e9c511eba3450bed1e77882e; _uetvid=f46858d0e9c511eb92dc2f5cc253c3a9; _br_uid_2=uid%3D7941846393536%3Av%3D11.8%3Ats%3D1626832200171%3Ahc%3D11; AMCV_5E85123F5245B3520A490D45%40AdobeOrg=-330454231%7CMCIDTS%7C18830%7CMCMID%7C60092091741279043604231464560235695792%7CMCAAMLH-1627461102%7C11%7CMCAAMB-1627461102%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCCIDH%7C931085087%7CMCOPTOUT-1626861280s%7CNONE%7CMCAID%7CNONE%7CvVersion%7C3.1.2; mp_bergdorf_goodman_mixpanel=%7B%22distinct_id%22%3A%20%2217ac6c149bd360-068fb4ff39ae4e-6373260-104040-17ac6c149beb64%22%2C%22bc_persist_updated%22%3A%201626832193983%7D; _px2=eyJ1IjoiMTM1ZjI2YTAtZTlmZS0xMWViLWJkNDgtOTdlOTA0OTVmNjhiIiwidiI6IjBhYjgxOWY3LWU5YzYtMTFlYi04M2Y3LTAyNDJhYzEyMDAwOSIsInQiOjE2MjY4NTY2MDM5MzIsImgiOiI4ZWFiMjhkMDMwZWY3OGUwMmVmNmY5ZjAxYTA1MDE4ODQzODUxY2U1N2U3YWYyYjlmM2M0NjI1MTUxMTIyM2I4In0=; dtPC=10$256301678_356h-vCFOEAARJAKQPIGGVUDRNORFDBTKHGKTF-0e3; load_times=2.45_4.76; rxvt=1626858164155|1626855929730; dtLatC=1; s_tp=20032; s_ppv=https%253A%2F%2Fwww.bergdorfgoodman.com%2Fc%2Fdesigners-a-z-cat000001%2C4%2C4%2C716; om_prev_page={"ppv":"3"}; TLTSID=77254F8EE9FE10E9FE2DAC94B266C315; TLTUID=77254F8EE9FE10E9FE2DAC94B266C315; account=DT4; dtCookie=10$D359EB2AE3E945DF9B413458AD225C46|68bd3ff149c8f751|1; DYN_USER_CONFIRM=213d81eb3645db6faeea6de6149b4cb1; DYN_USER_ID=7251697604; JSESSIONID=W5b65kikUw660pUHocc42C3g5YYTYr0rBeje5jd5.jsession; W2A=3003973642.57185.0000; WID=7251697604; _cplid=1626856469527150; _optanalytics=; _optuid=1626856469527377; _pxhd=j6NRvCJn1NrOozmWc-KHCBSeSsNjSvK4QNFcqdkIem6B-VvJcdiyJ5omX6AmbdacMr2K8EGeYUsVrpXpGJpR6A==:kG/yJmlFztXrV3sdSqJszSKOxejiCz7EURl0B-s1Ki5h-qCrguOiIITTgZHjjbx6TsFBj9mBSUblsptwI-BSHK8GGKzPMu9jMl/yEtBSHSU=; tms_data="{DT-2017.03}a3HwxssoiZzaMm5Pj2Bv6L13Gv8Ad/WZkJm2zLBiJ21ld4dfj9JnVCkhgm80R6HP7xq2mB+8hifNNcO91uyLeEFeMZtOQA406+Ht/s9AE+TfcYb/sMCrG5GtCWrOFhGcgoN5MKuLYDMlj6mQ0OjfPW1iVtMbd9Hi4Mk+yx4yZIi+wIEacND2v0yTe3M4NNS9SFFpjlsimIJzzKJyv9euiS7OkVBY+GUZF+ecU+kOb0bDV95v1JXbEap0WdnnZKEWr1bSVdLtV3YL+wJ35sjOS3Jon/EvBYTSJNYqcXMGjZtDDYYaL89+JdL7JpIKrmmRshJZi/ScaaRXXVL4yctoNrO743/x7UlvBPuoDUtTizU4kmkms2yRa4ls+pmS+Sl/dICbyH0ULzWe1TwUutTMkTiZQDhoFs2ju/fPGKxNvPevWTDX/yHg4qfwkDQ+IiOC3MNbpm4ZUdKZ4DyWzdy1BQfwtpEgBXJC/J23yoLJkLc87s3pecRmzBRk6sGBCCUtOuGoPrJbdAJBlecQR4OIhlXsYjSn0Ex7uWzt8TfhE1OqdcCg2iP/iKqMSd/H11i+xIN0LxrkyzcneLN/46/gDU2hhZ0I3BHoZ4FG5fEYN/mHkMO/aPXYr1iaNO3QzJOEFDnFcR7fM9u8zw+VQBr5+Q36xLcEVKkObOcTdiH7ecwzOz3k4eb7x/r3+L0mO6V2WKMtrlCMxpzVvr0YAvYICsKi8ag80EH9RXZ8KuaFRPi51xt415JH1zVDRd7reb37XAjhrrw1iyO8RFZTyy6NGA49kcyt5qqEtLnNF8HBP5wEY5ZmUdX/IhTUjckIBZ1sw2AQSUsoJmJle2TXB+0SLKXPpQMuapwqsGg6B2sKOB6iz4omj8kVw23zSEZ60E9UpRpQ/5ORQ2U75a/o2uzzGARv8jm+3JKuyzaeXIDU+iwQAO/226oO/8iYqEZPGX17f5m4Y0xZU1CYaVphIJtO4w=="'
        }

    is_debug = True
    custom_debug_settings = {
        # 'MONGODB_SERVER': '127.0.0.1',
        # 'MONGODB_DB': 'fashionspider',
        # 'MONGODB_COLLECTION': 'fashions_pider',
        'MONGODB_COLLECTION': 'bergdorfgoodman',
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'INFO',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ALWAYS_STORE': False,
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60,  # 秒
        # 'HTTPCACHE_DIR': "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache",
        'DOWNLOADER_MIDDLEWARES': {
            # 'overseaSpider.middlewares.OverseaspiderDownloaderMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.DummyPolicy',
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.RFC2616Policy',
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):

        url_list = ["https://www.bergdorfgoodman.com/c/designers-a-z-cat000001"]
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
        brand_url_list = response.xpath(
            "//a[@itemprop='significantLink']/@href").getall()
        # # print(brand_url_list)

        for url in brand_url_list:
            url = response.urljoin(url).split("?")[0] + "?page=1"
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                headers=self.headers,
                # dont_filter=True,
            )

    def parse_list(self, response):
        """商品列表页"""
        # product_json_data = json.loads(response.text)
        # # print("*"*100)
        # # print("url:",response.url)
        # # print("begin")

        detail_url_list = response.xpath(
            '//div[contains(@class,"product-list")]/div[contains(@class,"product")]/a[contains(@target,"self")]/@href').getall()

        if detail_url_list:

            # # print(detail_url_list)
            # print(f"当前商品列表页有{len(detail_url_list)}条数据")

            for detail_url in detail_url_list:
                detail_url = response.urljoin(detail_url)
                # print("详情页url:"+detail_url)
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    headers=self.headers,
                )

            next_page_url = response.xpath('//a[@aria-label="Next"]/@href').get().strip() if response.xpath(
                '//a[@aria-label="Next"]/@href') else None

            if next_page_url:
                next_page_url = response.urljoin(next_page_url)
                # print("下一页:"+next_page_url)
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
        # # print("*"*100)
        # # print("详情页了了了了",response.url)
        items = ShopItem()

        html_json_data = response.xpath('//script[@type="application/json"]//text()').get()
        json_data = json.loads(html_json_data)
        json_data = defaultdict(lambda: None, json_data)

        product_json_data = json_data["productCatalog"]["product"]

        items["url"] = response.url

        is_outofstock = product_json_data["isOutOfStock"] if "isOutOfStock" in product_json_data else None
        if not is_outofstock and "linkedData" in product_json_data:
            if len(product_json_data["linkedData"]) > 0:

                items["name"] = product_json_data["linkedData"]["name"] if "name" in product_json_data[
                    "linkedData"] else None
                items["brand"] = product_json_data["linkedData"]["brand"] if "brand" in product_json_data[
                    "linkedData"] else None
                if "hierarchy" in product_json_data:
                    detail_cat_list = []
                    for key in product_json_data["hierarchy"][0]:
                        detail_cat_list.append(product_json_data["hierarchy"][0][key])
                    items["cat"] = detail_cat_list[-1]

                    items["detail_cat"] = '/'.join(detail_cat_list)

                price_json = product_json_data["price"]
                if "adornments" in price_json:
                    items["original_price"] =str(price_json["adornments"][0]["price"])
                    items["current_price"] = str(price_json["adornments"][1]["price"])
                else:
                    items["current_price"] =str(price_json["retailPrice"])
                    items["original_price"] =str(price_json["retailPrice"])

                items["description"] = self.filter_text(
                    product_json_data["linkedData"]["description"]) if "description" in product_json_data[
                    "linkedData"] else None

                items["source"] = website

                img_list = response.xpath(
                    '//div[contains(@class,"slick-track")]/div[@data-index and contains(@class,"slick-slide")]//img/@src').getall()
                img_list = list(set(img_list))

                img_list = ["https:" + img.strip() for img in img_list]

                items["images"] = img_list

                sku_list = list()
                sku_json_list = product_json_data["skus"] if "skus" in product_json_data else None

                if sku_json_list:
                    for sku in sku_json_list:
                        if "inStock" in sku and sku["inStock"] == True:
                            sku_info = SkuItem()
                            sku_att = SkuAttributesItem()
                            sku_info['sku'] = sku["id"] if "id" in sku else None
                            sku_att['colour'] = sku["color"]["name"] if "name" in sku["color"] else None
                            sku_att['size'] = sku["size"]["name"] if "name" in sku["size"] else None

                            sku_info['attributes'] = sku_att
                            sku_info['original_price'] = items["original_price"]
                            sku_info['current_price'] = items["current_price"]
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

                # print(items)
                yield items
                # self.check_item(items)
