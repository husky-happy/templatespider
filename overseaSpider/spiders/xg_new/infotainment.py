# -*- coding: utf-8 -*-
import re
import json
import time
import scrapy
import html
import requests
from hashlib import md5
from overseaSpider.util.utils import isLinux
from scrapy.selector import Selector

from overseaSpider.items import ShopItem, SkuAttributesItem, SkuItem

author = '方块'
website = 'infotainment'
domain_name = 'infotainment.com'
url_prefix = 'https://www.infotainment.com'

headers = {
}
cat_type = False#自定义
detail_cat_type = False#自定义
pagehtml = None



#sku_list
def translate_sku_data(raw_sku_data, options_arr):
    sku_item = SkuItem()
    sku_item['current_price'] = convert_currency(float(raw_sku_data['price']))
    sku_item['original_price'] = convert_currency(float(raw_sku_data['compare_at_price'])) if raw_sku_data[
                                                                                                  'compare_at_price'] and float(
        raw_sku_data['compare_at_price']) != 0 else sku_item['current_price']
    sku_item['imgs'] = [raw_sku_data['featured_image']['src']] if raw_sku_data['featured_image'] else []

    sku_attributes_item = SkuAttributesItem()
    other_dict = {}
    for i in range(3):
        optionTitle = raw_sku_data['option' + str(i + 1)]
        if optionTitle and options_arr[i]:
            optionName = options_arr[i]['name'].strip()
            if 'size' in optionName.lower():
                sku_attributes_item['size'] = optionTitle
            elif 'color' in optionName.lower() or 'colour' in optionName.lower():
                sku_attributes_item['colour'] = optionTitle
            else:
                other_dict[optionName] = optionTitle
                # sku_attributes_item['other'] = {optionName: optionTitle}
    if other_dict:
        sku_attributes_item['other'] = other_dict
    sku_item['attributes'] = sku_attributes_item
    return sku_item

#cat与detail_cat
def parse_category_by_product_type(product_type, full):
    separators = [' - ', ' > ', '>']
    for separator in separators:
        if separator in product_type:
            arr = product_type.split(separator)
            arr = list(map(lambda cat: cat.replace("/", "／"), arr))
            if full:
                return '/'.join(arr)
            else:
                return arr[-1]
    return product_type.replace("/", "／")



#float格式转换
def convert_currency(price):
    return '{:.2f}'.format(price)

#现价
def item_display_price(skus):
    old_min_price = skus[0].get('price', None)
    for sku in skus:
        new_min_price = sku.get('price', None)
        if new_min_price and old_min_price:
            old_min_price = min(float(new_min_price), float(old_min_price))
    if not old_min_price:
        old_min_price = 0
    return convert_currency(old_min_price)

#原价
def item_original_price(skus):
    old_max_price = 0
    for sku in skus:
        compare_at_price = sku.get('compare_at_price', None)
        if compare_at_price:
            old_max_price = max(float(compare_at_price), float(old_max_price))
    return convert_currency(old_max_price) if old_max_price > 0 else item_display_price(skus)

#available是否存在，price是否大于0
def item_is_available(skus):
    if skus:
        for sku in skus:
            if bool(sku['available']) and float(sku['price']) > 0:
                return True
    return False




class MyCrawlSpider(scrapy.Spider):
    name = website

    # 域名

    @classmethod
    def update_settings(cls, settings):
        # settings.setdict(getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug', False) else 'custom_settings', None) or {}, priority='spider')
        custom_debug_settings = getattr(cls, 'custom_debug_settings' if getattr(cls, 'is_debug',
                                                                                False) else 'custom_settings', None)
        system = isLinux()
        if not system:
            # 如果不是服务器, 则修改相关配置
            custom_debug_settings["HTTPCACHE_ENABLED"] = False
            custom_debug_settings["HTTPCACHE_DIR"] = "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache"
            custom_debug_settings["MONGODB_SERVER"] = "127.0.0.1"
        settings.setdict(custom_debug_settings or {}, priority='spider')

    def __init__(self, **kwargs):
        super(MyCrawlSpider, self).__init__(**kwargs)
        self.counts = 0
        setattr(self, 'author', author)

    is_debug = True
    custom_debug_settings = {
        'MONGODB_COLLECTION': website,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'DEBUG',
        'COOKIES_ENABLED': False,
        'HTTPCACHE_ALWAYS_STORE': False,
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 7 * 24 * 60 * 60,  # 秒
        # 'HTTPCACHE_DIR': "/Users/cagey/PycharmProjects/mogu_projects/scrapy_cache",
        'DOWNLOADER_MIDDLEWARES': {
            # 'overseaSpider.middlewares.PhantomjsUpdateCookieMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderDownloaderMiddleware': 543,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware': 400,
            # 'overseaSpider.middlewares.OverseaspiderProxyMiddleware_Domestic': 400,
            'overseaSpider.middlewares.OverseaspiderUserAgentMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'overseaSpider.pipelines.OverseaspiderPipeline': 300,
        },
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.DummyPolicy',
        # 'HTTPCACHE_POLICY': 'scrapy.extensions.httpcache.RFC2616Policy',
        'HTTPCACHE_POLICY': 'overseaSpider.middlewares.DummyPolicy',
        'DOWNLOAD_HANDLERS': {
            # "https": "overseaSpider.downloadhandlers.Ja3DownloadHandler",
            # "https": "overseaSpider.downloadhandlers.HttpxDownloadHandler",
            # 'https': 'scrapy.core.downloader.handlers.http2.H2DownloadHandler',
        }
    }

    # 不改变顺序去重(list)
    def delete_duplicate(self, oldlist):
        newlist = list(set(oldlist))
        newlist.sort(key=oldlist.index)
        return newlist

    # 过滤html标签
    def filter_html_label(self, text, type):
        text = str(text)
        text = html.unescape(text)
        # 注释，js，css
        filter_rerule_list = [r'(<!--[\s\S]*?-->)', r'<script[\s\S]*?</script>', r'<style[\s\S]*?</style>']
        for filter_rerule in filter_rerule_list:
            html_labels = re.findall(filter_rerule, text)
            for h in html_labels:
                text = text.replace(h, ' ')
        html_labels = re.findall(r'<[^>]+>', text)  # html标签单独拿出
        if type == 1:
            for h in html_labels:
                text = text.replace(h, ' ')
        filter_char_list = [
            u'\x85', u'\xa0', u'\u1680', u'\u180e', u'\u2000', u'\u200a', u'\u2028', u'\u2029', u'\u202f', u'\u205f',
            u'\u3000', u'\xA0', u'\u180E', u'\u200A', u'\u202F', u'\u205F', '\t', '\n', '\r', '\f', '\v',
        ]
        for f_char in filter_char_list:
            text = text.replace(f_char, ' ')
        text = re.sub(' +', ' ', text).strip()
        return text

    def cats_func(self, url, headers, type):
        infos = ''
        global pagehtml
        if not pagehtml:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                pagehtml = Selector(text=res.text)
        if pagehtml:
            if type == 1:
                cat_text = pagehtml.xpath('(//div[@class="breadcrumbs-inner"]//li//a)[last()]').get()
                if cat_text:
                    cat_text = self.filter_html_label(cat_text, 1)
                    infos = cat_text
            if type == 2:
                cat_list = pagehtml.xpath('//div[@class="breadcrumbs-inner"]//li//a').getall()
                cat_list_text = ''
                if cat_list:
                    for cat1 in cat_list:
                        cat2 = self.filter_html_label(cat1, 1)
                        cat_list_text += (cat2 + '/')
                cat_list_text = cat_list_text.rstrip('/')
                if str(cat_list_text).strip() != '':
                    infos = cat_list_text
        return infos

    def start_requests(self):
        yield scrapy.Request(
            url=url_prefix + '/products.json?page=1&limit=250',
            callback=self.parse,
            cookies={
            'cart_currency': 'USD'
            }
        )  # limit 最大为 250，超过无效



    def parse(self, response):
        json_data = json.loads(response.text)
        items_list = json_data.get('products', None)

        for item_obj in items_list:
            if not item_is_available(item_obj.get('variants', None)):
                continue
            if len(list(item_obj.get('images', None))) == 0:
                continue

            items = ShopItem()

            page_url = None
            handle = item_obj.get('handle', None)
            if handle:
                page_url = url_prefix + '/products/' + str(handle).strip()
                items["url"] = str(page_url).strip()
            items["brand"] = item_obj.get('vendor', '')
            items["name"] = item_obj.get('title', '')

            items["source"] = website


            variants = item_obj.get('variants', None)
            if variants and len(variants) > 0:
                current_price = item_display_price(variants)
                if current_price != '0.00':
                    items["current_price"] = current_price

                original_price = item_original_price(variants)
                if original_price != '0.00':
                    items["original_price"] = original_price

            items["cat"] = ''
            items["detail_cat"] = ''
            product_type = item_obj.get('product_type', None)
            if cat_type and page_url:
                items["cat"] = self.cats_func(page_url, headers, 1)
            else:
                if product_type:
                    cat = parse_category_by_product_type(product_type, False)
                    if str(cat).strip() != '':
                        items["cat"] = cat
            if detail_cat_type and page_url:
                items["detail_cat"] = self.cats_func(page_url, headers, 2)
            else:
                if product_type:
                    detail_cat = parse_category_by_product_type(product_type, True)
                    if str(detail_cat).strip() != '':
                        items["detail_cat"] = detail_cat

            body_html = item_obj.get('body_html', '')
            if str(body_html).strip() != '':
                items["description"] = self.filter_html_label(body_html, 1)
            else:
                items["description"] = ''


            body_html = re.sub(r'[\t\n\r\f\v]', ' ', body_html)
            attribute_matches = list(re.finditer(r'(<strong[^><]*>([^><:]+):</strong>([^><]+))<', body_html))
            items['attributes'] = list()
            if len(attribute_matches) > 0:
                for match in attribute_matches:
                    items['attributes'].append(self.filter_html_label(match.group(2).strip() + ": " + match.group(3).strip(), 1))
                    body_html = body_html.replace(match.group(1), "")

            images = item_obj.get('images', None)
            images_list = list()
            if images:
                for image in images:
                    src = image.get('src')
                    if src:
                        images_list.append(src)
            if images_list:
                items["images"] = self.delete_duplicate(images_list)

            items["measurements"] = ["Weight: None", "Height: None", "Length: None", "Depth: None"]

            items["sku_list"] = list(map(lambda sku: translate_sku_data(sku, item_obj['options']), item_obj['variants']))
            try:
                status_list = list()
                status_list.append(items["source"])
                status_list.append(items["name"])
                status_list.append(items["original_price"])
                status_list.append(items["current_price"])
                status_list = [i for i in status_list if i]
                status = "-".join(status_list)
                items["id"] = md5(status.encode("utf8")).hexdigest()
                items["lastCrawlTime"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                items["created"] = int(time.time())
                items["updated"] = int(time.time())
                items['is_deleted'] = 0

                # print("==================")
                # print(items)
                yield items
            except Exception as e:
                print(repr(e))


        if len(items_list) > 0:
            page_num_infos = re.findall('page=(\d+)', response.url)
            if page_num_infos:
                page_num = int(page_num_infos[0])
                next_page_num = page_num + 1
                next_page_url = response.url.replace('page='+str(page_num), 'page='+str(next_page_num))
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse,
                    cookies={
                        'cart_currency': 'USD'
                    }
                )
