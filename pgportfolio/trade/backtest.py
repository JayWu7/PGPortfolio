from __future__ import absolute_import, division, print_function
import numpy as np
from pgportfolio.trade import trader
from pgportfolio.marketdata.datamatrices import DataMatrices
import logging
import time
from pgportfolio.tools.trade import calculate_pv_after_commission


class BackTest(trader.Trader):
    def __init__(self, config, net_dir=None, agent=None, agent_type="nn", init_BTC=1):
        trader.Trader.__init__(self, 0, config, 0, net_dir,
                               initial_BTC=init_BTC, agent=agent, agent_type=agent_type)
        if agent_type == "nn":
            data_matrices = self._rolling_trainer.data_matrices
        elif agent_type == "traditional":
            config["input"]["feature_number"] = 1
            data_matrices = DataMatrices.create_from_config(config)
        else:
            raise ValueError()
        self.__test_set = data_matrices.get_test_set()  # 存储数据的时候，每一个period分开存储，包括了相对于这个period的前n个period的价格信息
        # shape :  (26,3,11,31)
        self.__test_length = self.__test_set["X"].shape[0]
        self._total_steps = self.__test_length
        self.__test_pv = 1.0
        self.__test_pc_vector = []

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
        return self.__test_set["X"][-1]

    def __get_matrix_y(self):
        return self.__test_set["y"][self._steps, 0, :]

    def rolling_train(self, online_sample=None):
        self._rolling_trainer.rolling_train()

    def generate_history_matrix(self):  # 产生历史价格（过去30个period）信息，important
        inputs = self.__get_matrix_X()
        # inputs   class: numpy    shape:(3,11,31)
        if self._agent_type == "traditional":  # not this
            inputs = np.concatenate([np.ones([1, 1, inputs.shape[2]]), inputs], axis=1)
            inputs = inputs[:, :, 1:] / inputs[:, :, :-1]
        return inputs

    def _trade_body(self):
        self._current_error_state = 'S000'
        starttime = time.time()
        omega = self._agent.decide_by_history(self.generate_history_matrix(), self._last_omega.copy())
        # 使用历史价格信息和上一次weight产生这一次的weight
        ## omega: numpy.ndarray 记录每个asset分配到的BTC的比例，和为1  len=12
        self.trade_by_strategy(omega)
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

    def trade_by_strategy(self, omega):  ## important
        logging.info("the step is {}".format(self._steps))
        logging.debug("the raw omega is {}".format(omega))
        future_price = np.concatenate((np.ones(1), self.__get_matrix_y()))

        pv_after_commission = calculate_pv_after_commission(omega, self._last_omega, self._commission_rate)  # 计算手续费
        value_after_training = np.dot(omega, future_price)  # calculate the new value(without commission)
        portfolio_change = pv_after_commission * value_after_training  # >1 means portfolio value added
        self._calculate_total_commission_fee(pv_after_commission, value_after_training)  # 计算累积commission
        self._log_trade_detail(self._last_omega, omega, self._total_capital)  # 打印详细交易信息
        self._total_capital *= portfolio_change  # new portfolio value

        self._last_omega = pv_after_commission * omega * \
                           future_price / \
                           portfolio_change
        logging.debug("the portfolio change this period is : {}".format(portfolio_change))
        self.__test_pc_vector.append(portfolio_change)

    def _log_trade_detail(self, last, omega, capital):
        coins = ['BTC'] + self._coin_name_list
        for la, om, co in zip(last, omega, coins):
            if la > om:  # 有卖出
                sell = (la - om) * capital
                logging.info("  Selling {} btc's {}, the weight decreases from {} to {}".format(sell, co, la, om))
            elif la < om:  # 有加持
                buy = (om - la) * capital
                logging.info("  Buying {} btc's {}, the weight increases from {} to {}".format(buy, co, la, om))
            else:  # 持仓不变
                logging.info("  Holding *{}* positions".format(co))
