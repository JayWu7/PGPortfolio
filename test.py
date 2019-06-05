# from urllib.request import Request, urlopen
# from itertools import chain
# from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
#
# import json
#
# u = 'https://poloniex.com/public?start=1538323200&end=1551369600&period=300&currencyPair=USDT_BTC&command=returnChartData'
#
#
# def download_helper(url, divide=2):
#     tup = urlparse(url)
#     query = parse_qs(tup.query)
#     start = int(query['start'][0])
#     end = int(query['end'][0])
#     per = (end - start) // divide
#     jsons = []
#     for _ in range(divide):
#         mid = start + per
#         query['end'] = [str(mid)]
#         str_query = urlencode(query, doseq=True)
#         new_url = urlunparse(tup._replace(query=str_query))  # namedtuple alter the attribute)
#         print(new_url)
#         conn = urlopen(Request(new_url))  # 60s没打开则超时
#         json_str = json.loads(conn.read().decode(encoding='UTF-8'))
#         if 'error' in json_str and len(json_str) == 1:
#             return False  # 按照当前divide 分开抓取数据，仍然出错
#         jsons.append(json_str)
#         start = mid + 300
#         query['start'] = [str(start)]
#
#     return [item for json in jsons for item in json]
#
#
# import time
#
# st = time.time()
# jsons = download_helper(u)
# en = time.time()
# print(en - st)
from huobi.requstclient import RequestClient
from huobi.model.account import Account
from huobi.model import AccountType,OrderType,OrderState
from huobi.model import Balance
import os

request = RequestClient()
request.get_exchange_info()
# bal = request.get_account_balance_by_account_type(AccountType.SPOT)
# coins = ['btc','eth', 'eos', 'xrp', 'atom', 'ltc', 'etc', 'xmr', 'dash', 'zec', 'bch', 'bat']
# for cur in bal.balances:
#     if cur.currency in coins and cur.balance_type == 'trade':
#         print(cur.currency)
#         print(cur.balance)
# capital = 0.0
# capital += bal.get_balance('btc')[0].balance
# for coin in coins[1:]:
#     balance = bal.get_balance(coin)
#     balance_num = balance[0].balance
#     cur_price = request.get_last_trade(coin + 'btc').price
#     coin_value = balance_num * cur_price
#     capital += coin_value
#
# print(capital)

# trade = request.get_last_trade('ltcbtc')
# print(trade.price)
# print(trade.direction)

orders = request.get_historical_orders('etcbtc',OrderType)

# request.create_order(symbol='ltcbtc',account_type=AccountType.SPOT,order_type=OrderType.BUY_MARKET,amount=0.48273, price=None)