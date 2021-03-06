import base64
import re
import time
from datetime import datetime
from typing import Dict
from urllib.parse import quote
import hashlib
import collections
import ast
import requests
from dateutil.relativedelta import relativedelta
import pandas as pd
import random

def get_basic_auth_str(username, password):
    temp_str = username + ':' + password
    bytes_string = temp_str.encode(encoding="utf-8")  # 转成bytes string
    encode_str = base64.b64encode(bytes_string)  # base64 编码
    return 'Basic ' + encode_str.decode()


def decode_basic_auth_str(auth_str):
    bytes_string = auth_str.encode("utf-8")
    decode_str = base64.b64decode(bytes_string)
    return decode_str.decode("utf-8")


def create_form_data(link, secret):
    """
    生成 form_data, 通过模拟前端JS逻辑
    :param link: 网站的网址
    :param secret:
    :return: form_data

    >>> create_form_data('http://item.jd.hk/10429555538.html', 'c5c3f201a8e8fc634d37a766a0299218')
    """

    form_data = {
        'method': 'getHistoryTrend',
        'key': link,
        't': str(int(time.time() * 100000))[:13]  # 13 位时间戳
    }

    form_data: Dict = collections.OrderedDict(  # 按照 key 排序
        sorted(
            form_data.items(),
            key=lambda x: x[0])
    )

    token = secret  # secret 不变
    for k, v in form_data.items():
        token += quote(k, safe='') + quote(v, safe='')  # Python 默认不转义斜杠(safe) //, 前端 JavaScript 转义
    token += secret
    token = token.upper()  # 转成大写
    m = hashlib.md5()
    m.update(token.encode('utf-8'))  # 生成 md5 码
    token = m.hexdigest().upper()
    form_data['token'] = token  # 添加 token 
    return form_data


def create_auth():
    req = requests.get('http://tool.manmanbuy.com/HistoryLowest.aspx')
    if req.status_code == 200:
        history_price_html = req.text
        searchRet = re.search(r'id="ticket".+value="(?P<value>.+)"', history_price_html)
        if not searchRet:
            return ''
        ticket = searchRet.group('value')

        return 'BasicAuth ' + ticket[-4:] + ticket[:-4]
    return ''


class Product:
    def __init__(self, data):
        self.haveTrend = data['haveTrend']
        self.changePriceRemark = data['changPriceRemark']
        self.changePriceCount = data['changePriceCount']
        self.spUrl = data['spUrl']
        self.spPic = data['spPic']
        self.currentPrice = data['currentPrice']
        self.spName = data['spName']
        self.lowerDate = data['lowerDate']
        self.lowerPrice = data['lowerPrice']
        self.siteName = data['siteName']
        datePrices = ast.literal_eval('[' + data['datePrice'] + ']')
        self.datePrices = [DatePrice(d) for d in datePrices]


class DatePrice:
    def __init__(self, datePrice):
        self.date = datetime.fromtimestamp(datePrice[0] / 1000)
        self.price = datePrice[1]
        self.condition = datePrice[2]

    def __str__(self):
        return str(self.date) + ", " + str(self.price) + ", " + str(self.condition)


def 抓取一条数据(dt, cookie, index=0, link='https://item.jd.com/10429555538.html'):
    data = create_form_data(link, 'c5c3f201a8e8fc634d37a766a0299218')
    basic_auth = create_auth()
    resp = requests.post("http://tool.manmanbuy.com/api.ashx", data=data, headers={
        "Authorization": basic_auth,
        "Cookie": cookie,
        "Host": "tool.manmanbuy.com",
        "Origin": "http://tool.manmanbuy.com",
        "Referer": "http://tool.manmanbuy.com/historylowest.aspx",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    })
    resp_json = resp.json()
    print(resp_json)
    product = Product(resp_json['data'])
    price_list = product.datePrices

    今天 = datetime.today()
    今天 = 今天.replace(hour=0, minute=0, second=0, microsecond=0)
    今天_min = price_list[-1]

    二十五月 = 今天 + relativedelta(months=-25)
    二十五月_list = list(filter(lambda x: 二十五月 < x.date < 今天, price_list))
    二十五月_min = min(二十五月_list, key=lambda x: x.price)

    九十天 = 今天 + relativedelta(days=-90)
    九十天_list = list(filter(lambda x: 九十天 < x.date < 今天, price_list))
    九十天_min = min(九十天_list, key=lambda x: x.price)

    六十天 = 今天 + relativedelta(days=-60)
    六十天_list = list(filter(lambda x: 六十天 < x.date < 今天, price_list))
    六十天_min = min(六十天_list, key=lambda x: x.price)

    三十天 = 今天 + relativedelta(days=-30)
    三十天_list = list(filter(lambda x: 三十天 < x.date < 今天, price_list))
    三十天_min = min(三十天_list, key=lambda x: x.price)

    dt.loc[index] = {
        "品牌": product.siteName, "名称": product.spName, "链接": product.spUrl,
        "25时间": 二十五月_min.date, "25价格": 二十五月_min.price, "25条件": 二十五月_min.condition,
        "90时间": 九十天_min.date, "90价格": 九十天_min.price, "90条件": 九十天_min.condition,
        "60时间": 六十天_min.date, "60价格": 六十天_min.price, "60条件": 六十天_min.condition,
        "30时间": 三十天_min.date, "30价格": 三十天_min.price, "30条件": 三十天_min.condition,
        "当前时间": 今天_min.date, "当前价格": 今天_min.price, "当前条件": 今天_min.condition,
    }


if __name__ == '__main__':
    # auth_str = get_basic_auth_str('Tom', 'test')  # Basic VG9tOnRlc3Q=
    # decode_str = decode_basic_auth_str('VG9tOnRlc3Q=')  # Tom:test

    dt = pd.DataFrame(columns=["品牌", "名称", "链接",
                               "25时间", "25价格", "25条件",
                               "90时间", "90价格", "90条件",
                               "60时间", "60价格", "60条件",
                               "30时间", "30价格", "30条件",
                               "当前时间", "当前价格", "当前条件",
                               ])

    with open('config', 'r') as f:
        cookie = f.readline()
        f.close()

    with open('urls.txt', 'r') as f:
        i = 0
        for line in f.readlines():
            try:
                抓取一条数据(dt=dt, cookie=cookie, index=i, link=line)
            except Exception as e:
                dt.loc[i] = {

                }
            i += 1
            time.sleep(random.randint(8, 15))
        f.close()

    dt.to_excel(str(datetime.now()).replace(":", "_") + ".xlsx")
