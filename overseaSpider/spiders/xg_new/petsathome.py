# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import requests
from hashlib import md5
import random
import itertools
from scrapy.selector import Selector
import httpx

from overseaSpider.util.utils import isLinux, filter_text
from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem
from overseaSpider.util import item_check
from overseaSpider.util.scriptdetection import detection_main
from lxml import etree

website = 'petsathome'

class PetsathomeSpider(scrapy.Spider):
    name = website
    # allowed_domains = ['petsathome.com']
    # start_urls = ['http://petsathome.com/']
    domain_url = "https://www.petsathome.com/".strip("/")
    users_agent = [
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",

        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",

        "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
    ]
    user_agent = random.choice(users_agent)
    headers_res = {"user-agent": user_agent}
    headers = {
        'authority': 'www.petsathome.com',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cookie': 'logglytrackingsession=f31395b8-ea63-4e46-a04f-be70e1157790; _gcl_au=1.1.78536439.1637043622; gtmPetPlanCampaign=PHDRCT10; _pahGA=GA1.2.558932448.1637043622; _pahGA_ga=GA1.1.558932448.1637043622; _scid=c219926f-fea2-43e2-9450-84abdbb89875; _hjid=313a5ae6-9d86-4665-8e5a-87cdcaf4e986; _hjCachedUserAttributes=eyJhdHRyaWJ1dGVzIjp7IkV4aXN0aW5nIEN1c3RvbWVyIjpmYWxzZSwiSGFzIEJpcmQiOjAsIkhhcyBDYXQiOjAsIkhhcyBDaGlja2VuIjowLCJIYXMgRG9nIjowLCJIYXMgRmlzaCI6MCwiSGFzIEhvcnNlIjowLCJIYXMgUmVwdGlsZSI6MCwiSGFzIFNtYWxsIFBldCI6MCwiSGFzIFdpbGRsaWZlIjowLCJOZXcgQ3VzdG9tZXIiOnRydWUsIlZJUC9QdXBweS9LaXR0ZW4gQ2x1YiBNZW1iZXIiOmZhbHNlfSwidXNlcklkIjpudWxsfQ==; ivid=19ba1a72a77d1e1528a7ec583dc7a2d27e947c77f5; _fbp=fb.1.1637043624194.1840586595; WC_SESSION_ESTABLISHED=true; WC_PERSISTENT=cW7JCK%2bPKfvln4DhYVuHe5xxvUA%3d%0a%3b2021%2d11%2d16+06%3a20%3a24%2e725%5f1637043620555%2d111563%5f10151%5f%2d1002%2c%2d1%2cGBP%5f10151; WC_AUTHENTICATION_-1002=%2d1002%2cdnP0i6IVHnDZJ6f2igu4RDjTSxk%3d; WC_ACTIVEPOINTER=%2d1%2c10151; WC_USERACTIVITY_-1002=%2d1002%2c10151%2cnull%2cnull%2cnull%2cnull%2cnull%2cnull%2cnull%2cnull%2caKGCMW0ukzpMrLkz95UiR6xP8LoUqU7GA0mG9lJy3YfDAf6xdfIq%2fJw1iLn5jU4W%2f9oJB4zogZ2i%0aKeUtqhdHhdSDgMnuvRFYFOdQPtwFdEdsQZT2ERlninhqDhStCaUqkI941R6QH66thMKztPubAg%3d%3d; __qca=P0-881642906-1637043624261; _cs_c=1; __pr.96n=s6JlWBb-Un; cookiePolicy=true; WC_MOBILEDEVICEID=0; gtmPetPlanData=s=direct|m=direct|c=direct|k=|co=|gc=; _ga_CNSHY37GMP=GS1.1.1637057134.2.0.1637057556.0; _ga=GA1.2.558932448.1637043622; cf_chl_2=f85435f9141caff; cf_chl_prog=x11; cf_clearance=9y2aDb1tt.dOqm8cyizlcozw.xlN73ofEdPIM.oyMuU-1639465943-0-150; tduc=1; JSESSIONID=0000mcs0OI7HFzDbDMOIKcLuT9J:f8p5cloeN; WC_GENERIC_ACTIVITYDATA=[5254488039%3atrue%3afalse%3a0%3aj6f9XcqphnpJ5S2kXrQl4KuPPu0%3d][com.ibm.commerce.store.facade.server.context.StoreGeoCodeContext|null%26null%26null%26null%26null%26null][MySavedPaymentContext|null%26null%26null%26null%26null%26null%2610651][CTXSETNAME|Store][com.ibm.commerce.context.globalization.GlobalizationContext|%2d1%26GBP%26%2d1%26GBP][DDSetupBankDetailsContext|null%26null%26null%26null%26null%26null%26null%26null%26null%26null][com.ibm.commerce.context.base.BaseContext|10151%26%2d1002%26%2d1002%26%2d1][com.ibm.commerce.context.experiment.ExperimentContext|null][com.ibm.commerce.context.entitlement.EntitlementContext|10003%2610003%26null%26%2d2000%26null%26null%26null][com.ibm.commerce.giftcenter.context.GiftCenterContext|null%26null%26null][PPContext|null%26null%26null%26null%26null%26null%26null%26null%26null%267141899][DDSetupContext|null%26null%26null%26null%26null%26null%26null%26null%26null][com.ibm.commerce.context.audit.AuditContext|1637043620555%2d111563][com.ibm.commerce.catalog.businesscontext.CatalogContext|10651%26null%26false%26false%26false]; _pahGA_gid=GA1.2.581750694.1639465947; _hjSessionUser_1163562=eyJpZCI6ImQ3MThmZWQ0LWQ0NmMtNTFkOC1iZmZlLWFkNDY1YTYxODhhMiIsImNyZWF0ZWQiOjE2Mzk0NjU5NDg0NDEsImV4aXN0aW5nIjp0cnVlfQ==; _hjSession_1163562=eyJpZCI6ImVjNWRkZDkxLWQxZWEtNDg5YS1hMjQ2LTVkZWYwNmEwZTllNiIsImNyZWF0ZWQiOjE2Mzk0NjU5NDg0NTZ9; _hjIncludedInSessionSample=0; _hjAbsoluteSessionInProgress=0; _sctr=1|1639411200000; _mitata=YTI2YTFmOWQ2ZTdlYzgxNGVkNDJjZTk0MjZhN2UwODYwNGYxODMzNzA4M2FhMzkyNDEwOWJlODYxZjE1NDJjMg==_/@#/1639466244_/@#/mqacin2luwjywdca_/@#/000; _gat_UA-6022948-2=1; gtmPetPlanSession=1639466199604; stc111507=env:1639465947%7C20220114071227%7C20211214074640%7C7%7C1012822:20221214071640|uid:1637043622600.1235975948.5733342.111507.1054868567:20221214071640|srchist:1012822%3A1%3A20211217062022%7C1012823%3A1637048128%3A20211217073528%7C1012822%3A1639465947%3A20220114071227:20221214071640|tsa:1639465947904.805233259.8151612.3293769686456405.6:20211214074640; _uetsid=31a010a05cad11ecac6229569f6fc0f5; _uetvid=4752ea2046a511eca92ce9c10b386e6b; ABTasty=uid=yaxrg4f1aftex76r&fst=1637043622306&pst=1637057127930&cst=1639465946992&ns=3&pvt=34&pvis=7&th=644226.799708.32.7.3.1.1637043633047.1639466200188.1_671550.832538.34.7.3.1.1637043622630.1639466200181.1_689421.855068.24.4.2.1.1637043656839.1639466200232.1_702568.871871.2.2.1.1.1637043622829.1637048129149.1_732689.910335.32.7.3.1.1637043634223.1639466200313.1_743468.923757.32.7.3.1.1637043634232.1639466200316.1_752810.935672.34.7.3.1.1637043622631.1639466200183.1_781108.971024.7.7.1.1.1639465947884.1639466200318.1_789741.981360.4.4.1.1.1639465947889.1639466200321.1; ABTastySession=mrasn=&sen=56&lp=https%253A%252F%252Fwww.petsathome.com%252Fshop%252Fen%252Fpets%252Fbeloved-bebugfree-repel-spray-200ml%253F__cf_chl_jschl_tk__%253D2_gO6DcIcXrh3ujycCli_qIEEm.xhXoodrBhebXTsE4-1639465940-0-gaNycGzNEv0; rr_rcs=eF4FwbENgDAMBMAmFbPwUmI7j7IBa0S2I1HQAfNzV8rrZx59uAbhSxLmNuFTBCk9gxI053Z_zxV7V0OjDiOlVtEKAu0HmvER2g; aluid=6APPV6+LBWtHWLR3ZE1RgKbkVqCbMw9kT4VaugEUwYYfnFFYGS+EB0ultiuxdSncyfd0cCx74FOy3Mb/oaHyHg==; _cs_id=7810e2d9-97b6-a264-c2af-df6a410b4b63.1637043626.3.1639466203.1639465950.1.1671207626138; _cs_s=5.0.0.1639468003352; _br_uid_2=uid%3D3761142650197%3Av%3D12.1%3Ats%3D1637043625852%3Ahc%3D31; _pahGA_ga_CNSHY37GMP=GS1.1.1639465947.3.1.1639466229.16; _mitata=ZDU3MTRlNjA0ODQ4NjVkZGY1MGFmYzVlZTUyZDJlZDE4YWM3MWZiNzJlODMwMWFjNjgyMjdmMWU3MDBlZWJlMg==_/@#/1639466325_/@#/mqacin2luwjywdca_/@#/000; aluid=6APPV6+LBWtHWLR3ZE1RgDptdWu96737xdWjRfD0TgHd8+WDkNL3SAYs2dBXUb54GsgaKg4DbkA9d9SVo78BYA=='
    }

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            custom_debug_settings["CLOSESPIDER_ITEMCOUNT"]: 10
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            # # custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(PetsathomeSpider, self).__init__(**kwargs)
        self.counts = 1
        setattr(self, 'author', "阿斌")

    is_debug = True
    custom_debug_settings = {
        # 'REDIRECT_ENABLED': False,
        # 'HTTPERROR_ALLOWED_CODES': [410],
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ENABLED': False,
         # 'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60, # 秒
        'DOWNLOADER_MIDDLEWARES': {
            #'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            #'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        # 'DOWNLOAD_HANDLERS': {
        #     "https": "overseaSpider.downloadhandlers.HttpxDownloadHandler",
        # },
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
    }

    def start_requests(self):
        # maodian1
        url_list = [
                     # "https://www.petsathome.com/",
                     "https://www.petsathome.com/shop/en/pets/bakers-complete-chicken-and-vegetables",
                     "https://www.petsathome.com/shop/en/pets/beloved-bebugfree-repel-spray-200ml",
                       ]
        for url in url_list:
        #     print(url)
             yield scrapy.Request(
                 url=url,
                 # callback=self.parse,
                 callback=self.parse_detail,
                 meta={'h2': True},
                 headers=self.headers,
             )

    def parse(self, response):
        url_list = response.xpath("//section[contains(@class, 'dth-mega-menu')]/div//a/@href").getall()
        url_list = [u for u in url_list if "javascript:" not in u and "#" != u and "/" in u]
        url_list = [response.urljoin(url) for url in url_list]
        meta = response.meta
        meta["page"] = "1"
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                meta=response.meta,
                headers=self.headers,
            )

    def parse_list(self, response):
        """列表页"""
        url_list = response.xpath("//section[contains(@class, 'layout-product-tile-holder')]/a/@href").getall()
        url_list = [u for u in url_list if "javascript:" not in u and "#" != u and "/" in u]
        url_list = [response.urljoin(url) for url in url_list]
        for url in url_list:
            # print(url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                headers=self.headers,
                meta=response.meta,
            )

        if url_list:
            meta = response.meta
            meta["page"] = str(int(meta["page"]) + 1)
            if "currentPage=" in response.url:
                next_page_url = re.sub("currentPage=\d+&pageSize=24&orderBy=1", f"currentPage={meta['page']}", response.url)
            else:
                next_page_url = response.url + f"?currentPage={meta['page']}&pageSize=24&orderBy=1"
            next_page_url = response.urljoin(next_page_url)
            # print("下一页:"+next_page_url)
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse_list,
                headers=self.headers,
                meta=meta,
            )

    def parse_detail(self, response):
        currency = "£"
        """详情页"""
        items = ShopItem()
        items["url"] = response.url
        original_price = response.xpath("//span[contains(@class, 'pdp-price__was')]/text()").get()
        current_price = response.xpath("//span[contains(@id, 'offerPrice')]/text()").get()
        if "-" in current_price:
            current_price = current_price.split("-")[0].replace(currency, "").strip()
        else:
            current_price = current_price.replace(currency, "").strip()

        if original_price:
            if "-" in original_price:
                original_price = original_price.split("-")[0].replace("Was", "").replace(currency, "").strip()
            else:
                original_price = original_price.replace("Was", "").replace("was", "").replace(currency, "").replace(",", "").strip()
                if not original_price:
                    original_price = current_price
        else:
            original_price = current_price
        if not current_price:
            raise Exception("No price!!!")
        items["original_price"] = str(original_price).replace(",", "").replace(currency, "").strip()
        items["current_price"] = str(current_price).replace(",", "").replace(currency, "").strip()

        # attr_list = response.xpath("//table[contains(@class, 'additional-attributes')]/tbody/tr")
        # attributes = list()
        # for attr in attr_list:
        #     key = attr.xpath("./th/text()").get().strip()
        #     value = " ".join(attr.xpath("./td//text()").getall()).replace("\r", "").replace("\n", "").replace("  ", " ").strip()
        #     attributes.append(f"{key}: {value}")
        # items["attributes"] = attributes

        # brand = re.findall("\"brand\":.*?name\":\"(.*?)\"", response.text, re.S)
        brand = re.findall("\"brand\": \"(.*?)\"", response.text)
        # brand = response.xpath("//div[contains(@class, 'brand')]/a/text()").get()
        if brand and brand is not None:
            items["brand"] = brand[0].strip()
        else:
            items["brand"] = ""
        name = response.xpath("//h1[contains(@class, 'title')]/text()").getall()
        if not name:
            name = response.xpath("//meta[@property='og:title']/@content").getall()
        items["name"] = "".join(name).strip()

        description = response.xpath("//div[contains(@id, 'description')]//text()").getall()
        if not description:
            description = response.xpath("//meta[contains(@name, 'description')]/@content").getall()
        if description:
            items["description"] = filter_text("".join(description)).replace("  ", " ")
        else:
            items["description"] = ""
        items["source"] = website
        images_list = response.xpath("//ul[contains(@class, 'pdp-image-viewer__tn-list')]/li/@data-zoom").getall()
        if not images_list:
            images_list = response.xpath("//ul[contains(@class, 'pdp-image-viewer__tn-list')]/li/img/@src").getall()
            if not images_list:
                images_list = response.xpath("//img[contains(@id, 'pdp-full-image')]/@src").getall()
                # images_list = [re.sub("/\d+/", "/900/", i) for i in images_list]
        else:
            images_list = ["https:" + i if "http" not in i else i for i in images_list]
        images_list2 = list(set(images_list))
        images_list2.sort(key=images_list.index)
        items["images"] = images_list2

        Breadcrumb_list = response.xpath("//ul[contains(@class, 'breadcrumb')]/li//text()").getall()
        Breadcrumb_list = [b.strip() for b in Breadcrumb_list]
        if not Breadcrumb_list:
            items["cat"] = ""
            items["detail_cat"] = ""
        else:
            Breadcrumb_list2 = list(set(Breadcrumb_list))
            Breadcrumb_list2.sort(key=Breadcrumb_list.index)
            items["cat"] = Breadcrumb_list2[-1]
            items["detail_cat"] = "/".join(Breadcrumb_list2).strip("/")

        sku_list = []
        sku_info_list = re.findall("catentryAttrsJSON\s*=\s*(\[.*?\]);", response.text, re.S)
        if sku_info_list:
            sku_info_list = sku_info_list[0].replace("\r", "").replace("\n", "")
            sku_info_list = eval(sku_info_list)

            sku_data = re.findall("catentryItemsJSON\s*=\s*(\[.*?\]);", response.text, re.S)[0]
            sku_data = sku_data.replace("\r", "").replace("\n", "")
            sku_data = eval(sku_data)

            sku_data = sku_data[0]
            # print(sku_data)
            sku_info = sku_info_list[0]
            # print(sku_info)
            sku_type = list(sku_info.keys())[0]
            # print(sku_type)

            for sku_name, sku_num in sku_info[sku_type].items():

                sku_num_cur_data = sku_data[sku_num[0]]
                sku_item = SkuItem()
                original_price = sku_num_cur_data["wasPrice"]
                current_price = sku_num_cur_data["displayPrice"]
                if not original_price:
                    original_price = current_price
                sku_item["original_price"] = str(original_price).replace(",", "").replace(currency, "").strip()
                sku_item["current_price"] = str(current_price).replace(",", "").replace(currency, "").strip()

                sku_item["sku"] = str(sku_num[0])
                imgs = sku_num_cur_data["fullImage"]
                if not isinstance(imgs, list):
                    imgs = [imgs]
                imgs = ["https:" + i if "http" not in i else i for i in imgs]
                imgs = [re.sub("/[1-2]+00/", "/900/", i) for i in imgs]
                imgs2 = list(set(imgs))
                imgs2.sort(key=imgs.index)
                sku_item["imgs"] = imgs2
                sku_item["url"] = response.url
                attributes = SkuAttributesItem()
                if "size" == sku_type.lower():
                    attributes["size"] = sku_name
                elif "colour" == sku_type.lower() or "color" == sku_type.lower():
                    attributes["colour"] = sku_name
                else:
                    other = dict({sku_type: sku_name})
                    attributes["other"] = other
                sku_item["attributes"] = attributes
                sku_list.append(sku_item)
        # else:
        #     pass

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
        # detection_main(items = items,website = website,num = 5,skulist=True,skulist_attributes=True)
        yield items

