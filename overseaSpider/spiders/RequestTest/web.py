# import json
# from scrapy.selector import Selector
# import requests
#
# import codecs
# def SuccessScript(page):
#     cookies = {
#         'csrftoken': 'Km00OeEUWsLw1QK0YkOmiiRdBhReGtb6dBQXWJqdq7QxJpNx6hYBN6z4grYqvTyU',
#         'sessionid': '2c3exbc7g7l7zvyqr2dztmpvrb2v6on2',
#         'cookies': 'c599dbe0ed3866368cbd2f27d7b5c003',
#     }
#
#     headers = {
#         'Connection': 'keep-alive',
#         'Cache-Control': 'max-age=0',
#         'Upgrade-Insecure-Requests': '1',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
#         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
#         # 'Referer': 'http://20.81.114.208:9426/successscript/2',
#         'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
#     }
#
#     response1 = requests.get('http://20.81.114.208:9426/successscript/'+str(page), headers=headers, cookies=cookies, verify=False)
#     return response1.text
#
#
# cookies = {
#     'csrftoken': 'Km00OeEUWsLw1QK0YkOmiiRdBhReGtb6dBQXWJqdq7QxJpNx6hYBN6z4grYqvTyU',
#     'sessionid': '2c3exbc7g7l7zvyqr2dztmpvrb2v6on2',
#     'cookies': 'b0b127b119988781e2364d943697e125',
#     'sidebarStatus': '1',
#     'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2NDA3NjUwNDMsImlhdCI6MTY0MDc2NTAzMywiaXNzIjoia2VuIiwiZGF0YSI6eyJpZCI6IjYxYTQ4YTBjOTRiZGVjMjViMGQzMTY4MiIsImxvZ2luX3RpbWUiOjE2NDA3NjUwMzN9fQ.GHCs63-f4LYJ1QQfhYJiuLititvzw7xFCxrjEvxTn3c',
# }
#
# headers = {
#     'Connection': 'keep-alive',
#     'Accept': 'application/json, text/plain, */*',
#     'Authorization': 'JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2NDA3NjUwNDMsImlhdCI6MTY0MDc2NTAzMywiaXNzIjoia2VuIiwiZGF0YSI6eyJpZCI6IjYxYTQ4YTBjOTRiZGVjMjViMGQzMTY4MiIsImxvZ2luX3RpbWUiOjE2NDA3NjUwMzN9fQ.GHCs63-f4LYJ1QQfhYJiuLititvzw7xFCxrjEvxTn3c',
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
#     'Referer': 'http://20.81.114.208:9528/',
#     'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,an;q=0.6',
# }
#
# params = {
#     'filter': '{}',
#     # 'page_num': '1',
#     'page_size': '10',
# }
# # name_dict = dict()
# # for i in range(583):
# #     html = SuccessScript(i+1)
# #     selector = Selector(text=html)
# #     source = selector.xpath("//table//tr[position()>1]/td[2]/text()").getall()
# #     name = selector.xpath("//table//tr[position()>1]/td[9]/text()").getall()
# #     for j in range(len(source)):
# #         name_dict[source[j]]=name[j]
# #     print("抓取第"+str(i+1)+"页")
# # name_json=json.dumps(name_dict,ensure_ascii=False)
# # print(name_json)
# # f_six = codecs.open(r'./name_website.json','w','utf-8')
# f_six = open("./name_website.json", encoding='utf-8')
# # f_six.write(name_json)
# name_dict = json.load(f_six)
# file = open(r'./web_name.txt', mode='w')
# file2 = open(r'./no.txt',mode='w')
# file3 = open(r'./shopify.txt',mode='w')
# file4 = open(r'./requestError.txt',mode='w')
# num = 0
# for i in range(0,53):
#     params['page_num'] = str(i+1)
#     response = requests.get('http://20.81.114.208:9528/api/spiders/completed_spiders/completed_spiders', headers=headers, params=params, cookies=cookies, verify=False)
#     json_1 = json.loads(response.text)
#     # print(json_1)
#     for j in json_1['data']:
#         num = num+1
#         if j["source"] in name_dict:
#             file.write(j["source"]+":"+name_dict[j["source"]]+'\n')
#         else:
#             file2.write(j["source"]+'\n')
#         if "domain" in j:
#             url = "https://"+j['domain']
#             print("正在爬取第"+str(num)+"个")
#             try:
#                 new_response = requests.get(url,timeout=10)
#                 if new_response.text.find("cdn.shopify") != -1:
#                     file3.write(j["source"] + '\n')
#                     print(j["source"])
#             except:
#                 print(url+"    error1")
#                 new_url = "https://www."+j['domain']
#                 try:
#                     new_response1 = requests.get(new_url,timeout=10)
#                     if new_response1.text.find("cdn.shopify") != -1:
#                         file4.write(j["source"] + '\n')
#                         print(j["source"])
#                 except:
#                     print(new_url + "    error2")
#
#
#     print("写入第" + str(i + 1) + "页")
#     # file.close()
