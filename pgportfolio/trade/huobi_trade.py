from __future__ import absolute_import, division, print_function
import numpy as np
from pgportfolio.trade import trader
from pgportfolio.marketdata.datamatrices import DataMatrices
import logging
import time
from huobi_Python.huobi.requstclient import RequestClient
from huobi.model import AccountType, OrderType
from pgportfolio.constants import COINS_PRECISION


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
        print(self.__training_set["x"][-1])
        print(self.__test_set["X"][-1])
        return self.__test_set["X"][-1]  # 返回最近的一个period的历史数据

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
        self._current_error_state = 'S000'
        starttime = time.time()
        omega = self._agent.decide_by_history(self.generate_history_matrix(), self._last_omega.copy())
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
        capital = self.get_cur_capital()
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
        self._last_omega = omega

    def __start_huobi_order(self):  # 生成交易订单，开始交易
        while self.sell_orders:
            sell_info = self.sell_orders.pop()
            symbol = sell_info[0] + 'btc'
            self.request_client.create_order(symbol, AccountType.SPOT, OrderType.SELL_LIMIT, sell_info[1],
                                                    sell_info[2])  # return order id

        while self.buy_orders:
            buy_info = self.buy_orders.pop()
            symbol = buy_info[0] + 'btc'
            self.request_client.create_order(symbol, AccountType.SPOT, OrderType.BUY_LIMIT, buy_info[1],
                                                    buy_info[2])

    def __buy(self, coin, buy_btc_value, price):
        amount = self._exact_amount(coin, buy_btc_value / price)
        order_info = (coin, amount, price)
        self.buy_orders.append(order_info)
        print('buy: ', order_info)

    def __sell(self, coin, sell_btc_value, price):
        amount = self._exact_amount(coin, sell_btc_value / price)
        order_info = (coin, amount, price)
        self.sell_orders.append(order_info)
        print('sell: ', order_info)

    def __hold(self, coin):
        pass

    def get_cur_capital(self):
        bal = self.request_client.get_account_balance_by_account_type(AccountType.SPOT)
        btc_num = bal.get_balance('btc')[0].balance
        capital = btc_num
        self._coins_value['btc'] = btc_num
        for i, coin in enumerate(self.coins_name):
            balance_num = bal.get_balance(coin)[0].balance
            cur_price = self.request_client.get_last_trade(coin + 'btc').price
            self._prices[i] = cur_price
            coin_value = balance_num * cur_price
            self._coins_value[coin] = coin_value
            capital += coin_value

        self._total_capital = capital
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
