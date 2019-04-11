from urllib.request import Request, urlopen
from itertools import chain
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import json

u = 'https://poloniex.com/public?start=1538323200&end=1551369600&period=300&currencyPair=USDT_BTC&command=returnChartData'


def download_helper(url, divide=2):
    tup = urlparse(url)
    query = parse_qs(tup.query)
    start = int(query['start'][0])
    end = int(query['end'][0])
    per = (end - start) // divide
    jsons = []
    for _ in range(divide):
        mid = start + per
        query['end'] = [str(mid)]
        str_query = urlencode(query, doseq=True)
        new_url = urlunparse(tup._replace(query=str_query))  # namedtuple alter the attribute)
        conn = urlopen(Request(new_url))  # 60s没打开则超时
        json_str = json.loads(conn.read().decode(encoding='UTF-8'))
        if 'error' in json_str and len(json_str) == 1:
            return False  # 按照当前divide 分开抓取数据，仍然出错
        jsons.append(json_str)
        query['start'] = query['end']
        start = mid
    return [item for json in jsons for item in json]

import time
st = time.time()
jsons = download_helper(u)
en = time.time()
print(en - st)