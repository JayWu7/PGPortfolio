# poloniex  比特币交易市场
import socket
import json
import time
import sys
from datetime import datetime

if sys.version_info[0] == 3:
    from urllib.request import Request, urlopen
    from urllib.error import URLError
    from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
else:
    from urllib2 import Request, urlopen
    from urllib import urlencode

minute = 60
hour = minute * 60
day = hour * 24
week = day * 7
month = day * 30
year = day * 365

# Possible Commands
PUBLIC_COMMANDS = ['returnTicker', 'return24hVolume', 'returnOrderBook', 'returnTradeHistory', 'returnChartData',
                   'returnCurrencies', 'returnLoanOrders']


class Poloniex:
    def __init__(self, APIKey='', Secret=''):
        self.conn = None
        self.APIKey = APIKey.encode()
        self.Secret = Secret.encode()
        # Conversions
        # 格式化时间戳
        self.timestamp_str = lambda timestamp=time.time(), format="%Y-%m-%d %H:%M:%S": datetime.fromtimestamp(
            timestamp).strftime(format)
        self.str_timestamp = lambda datestr=self.timestamp_str(), format="%Y-%m-%d %H:%M:%S": int(
            time.mktime(time.strptime(datestr, format)))
        self.float_roundPercent = lambda floatN, decimalP=2: str(round(float(floatN) * 100, decimalP)) + "%"

        # PUBLIC COMMANDS
        self.marketTicker = lambda x=0: self.api('returnTicker')
        self.marketVolume = lambda x=0: self.api('return24hVolume')
        self.marketStatus = lambda x=0: self.api('returnCurrencies')
        self.marketLoans = lambda coin: self.api('returnLoanOrders', {'currency': coin})
        self.marketOrders = lambda pair='all', depth=10: \
            self.api('returnOrderBook', {'currencyPair': pair, 'depth': depth})
        self.marketChart = lambda pair, period=day, start=time.time() - (week * 1), end=time.time(): self.api(
            'returnChartData', {'currencyPair': pair, 'period': period, 'start': start, 'end': end})
        self.marketTradeHist = lambda pair: self.api('returnTradeHistory',
                                                     {'currencyPair': pair})  # NEEDS TO BE FIXED ON Poloniex

    #####################
    # Main Api Function #
    #####################
    def api(self, command, args={}):
        """
        returns 'False' if invalid command or if no APIKey or Secret is specified (if command is "private")
        returns {"error":"<error message>"} if API error
        """
        if command in PUBLIC_COMMANDS:
            url = 'https://poloniex.com/public?'
            args['command'] = command
            url = url + urlencode(args)
            try:
                self.conn = urlopen(Request(url), timeout=60)  # 60s没打开则超时
            except URLError:
                raise URLError('connect {} error!'.format(url))
            except socket.timeout:
                raise socket.timeout('The read json file operation timed out')
            else:  # no exception
                json_str = json.loads(self.conn.read().decode(encoding='UTF-8'))
                if 'error' in json_str and len(json_str) == 1:
                    for div in range(2, 20):
                        json_str = self.download_helper(url, div)
                        if json_str:  # != False
                            break
                    else:
                        raise ValueError('Data requested is too large, url is {}'.format(url))
                return json_str
        else:
            return False

    def download_helper(self, url, divide=2):
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
            start = mid + 300
            query['start'] = [str(start)]
        return [item for json in jsons for item in json]