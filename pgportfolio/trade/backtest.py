from __future__ import absolute_import, division, print_function
import numpy as np
from pgportfolio.trade import trader
from pgportfolio.marketdata.datamatrices import DataMatrices
import logging
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
        self.__test_set = data_matrices.get_test_set()
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
        return self.__test_set["X"][self._steps]

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

    def trade_by_strategy(self, omega):  ## important
        logging.info("the step is {}".format(self._steps))
        logging.debug("the raw omega is {}".format(omega))
        #  self.__get_matrix_y()  # [1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1.]     len=11
        future_price = np.concatenate((np.ones(1), self.__get_matrix_y()))
        # future_price # [1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1.]  len=12
        # 计算手续费
        pv_after_commission = calculate_pv_after_commission(omega, self._last_omega, self._commission_rate)
        # new portfolio value rate,after training and cut commission fee
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
                logging.info("  Holding *{}* positions}".format(co))
