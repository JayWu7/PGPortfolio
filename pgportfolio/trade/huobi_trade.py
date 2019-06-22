from __future__ import absolute_import, division, print_function
import numpy as np
from pgportfolio.trade import trader
from pgportfolio.marketdata.datamatrices import DataMatrices
import logging
import time
from huobi_Python.huobi.requstclient import RequestClient
from huobi.model import AccountType, OrderType, Order, OrderState
from pgportfolio.constants import COINS_PRECISION
from ..constants import FIVE_MINUTES as store_period


class HuobiTrader(trader.Trader):
    def __init__(self, config, net_dir=None, agent=None, agent_type="nn", init_BTC=1):
        trader.Trader.__init__(self, 1800, config, 0, net_dir,
                               initial_BTC=init_BTC, agent=agent, agent_type=agent_type)
        if agent_type == "nn":
            data_matrices = self._rolling_trainer.data_matrices
        elif agent_type == "traditional":
            config["input"]["feature_number"] = 1
            data_matrices = DataMatrices.create_from_config(config)
        else:
            raise ValueError()
        self.data_matrices = data_matrices
        self.__test_set = data_matrices.get_test_set()
        self.__test_length = self.__test_set["X"].shape[0]
        self._total_steps = self.__test_length
        self.__test_pv = 1.0
        self.__test_pc_vector = []
        api_key = '495dcb66-1f8b0442-92ea42e9-rfhfg2mkl3'
        secret_key = '58b07862-0c6faf4b-033c25c3-86454'
        self.request_client = RequestClient(api_key=api_key, secret_key=secret_key)
        self.coins_name = self.__generate_huobi_coin_name()
        self._coins_value = {}  # store the coin and its value in btc
        self._prices = [0.0] * 11  # store the current coin price
        self.buy_orders = []  # 买入订单
        self.sell_orders = []  # 卖出订单
        self.coins_precision = COINS_PRECISION

    def __generate_huobi_coin_name(self):  # 生成符合货币交易规范的coin name
        names = []
        for coin in self._coin_name_list:
            if coin == 'BCHABC':
                coin = 'bch'
            else:
                coin = coin.lower()
            names.append(coin)
        return names

    @property
    def test_pv(self):
        return self.__test_pv

    @property
    def test_pc_vector(self):
        return np.array(self.__test_pc_vector, dtype=np.float32)

    def _update_last_omega(self):  # 更新账户资金分配信息
        new_capital = self.get_cur_capital()
        coins = ['btc'] + self.coins_name
        for i, coin in enumerate(coins):
            self._last_omega[i] = round(self._coins_value[coin] / new_capital, 8)
        print(
            'Current asset is {}, omega is {}, sum is {}'.format(new_capital, self._last_omega, self._last_omega.sum()))

    def finish_trading(self):
        self.__test_pv = self._total_capital  # final portfolio value
        logging.info("Total commission cost is: {} {}".format(self._total_commission_cost, 'BTC'))
        # fig, ax = plt.subplots()
        # ax.bar(np.arange(len(self._rolling_trainer.data_matrices.sample_count)),
        #        self._rolling_trainer.data_matrices.sample_count)
        # fig.tight_layout()
        # plt.show()

    def _log_trading_info(self, time, omega):
        pass

    def _initialize_data_base(self):
        pass

    def _write_into_database(self):
        pass

    def __get_matrix_X(self):
        # return self.__test_set["X"][-1]
        return self.data_matrices._get_current_prices_input()  # 返回最近的一个period的历史数据

    def __get_matrix_y(self):
        return self.__test_set["y"][self._steps, 0, :]

    def rolling_train(self, online_sample=None):
        self._rolling_trainer.rolling_train()

    def generate_history_matrix(self):
        inputs = self.__get_matrix_X()
        if self._agent_type == "traditional":
            inputs = np.concatenate([np.ones([1, 1, inputs.shape[2]]), inputs], axis=1)
            inputs = inputs[:, :, 1:] / inputs[:, :, :-1]
        return inputs

    def _trade_body(self):
        print('Trade {} start'.format(self._steps))
        starttime = time.time()
        self._current_error_state = 'S000'
        self.data_matrices._update_data_matrix()
        self._update_last_omega()
        omega = self._agent.decide_by_history(self.generate_history_matrix(), self._last_omega.copy())
        print('Next period omega is {}'.format(omega))
        # 使用历史价格信息和上一次weight产生这一次的weight
        ## omega: numpy.ndarray 记录每个asset分配到的BTC的比例，和为1  len=12
        self._trade_by_strategy(omega)
        if self._agent_type == "nn":
            self.rolling_train()
        if not self.__class__.__name__ == "BackTest":
            self._last_omega = omega.copy()
        logging.info('total assets are %3f BTC' % self._total_capital)
        logging.debug("=" * 30)
        trading_time = time.time() - starttime
        if trading_time < self._period:
            logging.info("sleep for %s seconds" % (self._period - trading_time))
        self._steps += 1
        return self._period - trading_time

    def _trade_by_strategy(self, omega):  ## important
        logging.info("time is {}".format(time.asctime(time.localtime(time.time()))))
        logging.debug("the raw omega is {}".format(omega))
        self.__trade(omega)

    def __trade(self, omega):
        capital = self._total_capital
        for i, om in enumerate(omega[1:]):
            coin = self.coins_name[i]
            btc_value = om * capital - self._coins_value[coin]
            if btc_value > 0:  # need buy some this coin
                self.__buy(coin, btc_value, self._prices[i])
            elif btc_value < 0:
                self.__sell(coin, btc_value, self._prices[i])
            else:
                self.__hold(coin)
        self.__start_huobi_order()

    def __start_huobi_order(self):  # 生成交易订单，开始交易
        sell_symbols = []  # 储存卖出coin的symbol信息
        buy_symbols = []
        while self.sell_orders:
            sell_info = self.sell_orders.pop()
            symbol = sell_info[0] + 'btc'
            sell_symbols.append(symbol)
            self.__send_sell_order(sell_info[0], symbol, sell_info[1], sell_info[2])
        self.__monitor_sell_order(sell_symbols)
        while self.buy_orders:
            buy_info = self.buy_orders.pop()
            symbol = buy_info[0] + 'btc'
            buy_symbols.append(symbol)
            self.__send_buy_order(buy_info[0], symbol, buy_info[1], buy_info[2])
        self.__monitor_buy_order(buy_symbols)

    def __monitor_sell_order(self, symbols):  # 检查sell order 是否完成
        time.sleep(10)
        print('sleep 10 seconds for sell order to be trade.')
        res = []
        for symbol in symbols:
            orders = self.request_client.get_historical_orders(symbol, OrderState.SUBMITTED, OrderType.SELL_LIMIT)
            if orders:  # 此symbol order没有交易成功
                order = orders[0]
                try:  # 取消此order
                    self.request_client.cancel_order(symbol, order.order_id)
                    cur_price = self.__get_cur_price(symbol)
                    self.__send_sell_order(symbol[:-3], symbol, order.amount - order.filled_amount, cur_price)
                    res.append(symbol)
                except Exception as e:  # 出错
                    print(e)
                    print('cancel sell order wrong, symbol is: {}'.format(symbol))
        if res:
            self.__monitor_sell_order(res)
        else:
            print('All sell orders have finished!')
            return None

    def __monitor_buy_order(self, symbols):
        time.sleep(10)
        print('sleep 10 seconds for buy order to be trade.')
        res = []
        for symbol in symbols:
            orders = self.request_client.get_historical_orders(symbol, OrderState.SUBMITTED, OrderType.BUY_LIMIT)
            if orders:  # 此symbol order没有交易成功
                order = orders[0]
                try:  # 取消此order
                    self.request_client.cancel_order(symbol, order.order_id)
                    cur_price = self.__get_cur_price(symbol)
                    self.__send_buy_order(symbol[:-3], symbol, order.amount - order.filled_amount, cur_price)
                    res.append(symbol)
                except Exception as e:  # 出错
                    print(e)
                    print('cancel buy order wrong, symbol is: {}'.format(symbol))
        if res:
            self.__monitor_buy_order(res)
        else:
            print('All buy orders have finished!')
            return None

    def __buy(self, coin, buy_btc_value, price):
        amount = buy_btc_value / price
        order_info = (coin, amount, price)
        self.buy_orders.append(order_info)

    def __sell(self, coin, sell_btc_value, price):
        amount = abs(sell_btc_value) / price
        order_info = (coin, amount, price)
        self.sell_orders.append(order_info)

    def __hold(self, coin):
        pass

    def get_cur_capital(self):
        bal = self.request_client.get_account_balance_by_account_type(AccountType.SPOT)
        btc_num = bal.get_balance('btc')[0].balance
        capital = btc_num
        self._coins_value['btc'] = btc_num
        for i, coin in enumerate(self.coins_name):
            balance_num = bal.get_balance(coin)[0].balance
            cur_price = self.__get_cur_price(coin + 'btc')
            self._prices[i] = cur_price
            coin_value = balance_num * cur_price
            self._coins_value[coin] = coin_value
            capital += coin_value

        self._total_capital = capital
        # print('New capital omega is {}', [self._coins_value[coin] / capital for coin in self.coins_name])
        return capital

    def _exact_amount(self, coin, amount):  # 使amount为订单可接受精度
        if self.coins_precision[coin] == 0:
            amount = int(amount)
        else:
            amount_str = str(amount)
            if 'e' in amount_str:  # 以科学计数法表示
                amount_str = self._science_format_to_float(amount_str)
            precise_amount_str = amount_str[:amount_str.index('.') + self.coins_precision[coin] + 1]
            amount = float(precise_amount_str)
        return amount

    def _science_format_to_float(self, num_str: str) -> str:
        e = num_str.index('e')
        if '.' in num_str:
            point = num_str.index('.')
            part_1 = num_str[:point]
            part_2 = num_str[point + 1:e]
            zero_num = int(num_str[-1]) - len(part_1)
        else:
            part_1 = ''
            part_2 = num_str[:e]
            zero_num = int(num_str[-1]) - len(part_2)

        float_str = '0.' + ('0' * zero_num) + part_1 + part_2
        return float_str

    def __get_cur_price(self, symbol):
        while True:
            try:
                cur_price = self.request_client.get_last_trade(symbol).price
                return cur_price
            except:
                print('get the symbol:{} price wrong, try again! '.format(symbol))

    def __send_sell_order(self, coin, symbol, amount, price):
        amount = self._exact_amount(coin, amount)
        if amount == 0:
            print('sell 0 {}, Ignore!'.format(coin))
        elif self.coins_precision[coin] > 0 and amount < 10 ** -(self.coins_precision[coin] - 1):
            print('sell {} {}, too little, Ignore'.format(amount, coin))
        else:
            try:
                self.request_client.create_order(symbol, AccountType.SPOT, OrderType.SELL_LIMIT, amount, price)
            except Exception as e:
                print(e)
                print('this sell order went wrong, info: symbol-{},amount-{},price-{}'.format(symbol, amount, price))

    def __send_buy_order(self, coin, symbol, amount, price):
        amount = self._exact_amount(coin, amount)
        if amount == 0:
            print('buy 0 {}, Ignore!'.format(coin))
        elif self.coins_precision[coin] > 0 and amount < 10 ** -(self.coins_precision[coin] - 1):
            print('buy {} {}, too little, Ignore'.format(amount, coin))
        else:
            try:
                btc = self._get_current_btc()
                while btc < amount * price:  # 当前btc不足
                    amount = amount * 0.95
                amount = self._exact_amount(coin, amount)
                self.request_client.create_order(symbol, AccountType.SPOT, OrderType.BUY_LIMIT, amount, price)
            except Exception as e:
                print(e)
                print('this buy order went wrong, info: symbol-{},amount-{},price-{}'.format(symbol, amount, price))

    def _get_current_btc(self):  # 获得当前btc剩余量
        while True:
            try:
                bal = self.request_client.get_account_balance_by_account_type(AccountType.SPOT)
                btc_num = bal.get_balance('btc')[0].balance
                break
            except Exception as e:
                print(e)
                print('get the current btc value went wrong!')
        return btc_num
