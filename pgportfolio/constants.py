#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os import path

# 常量，一些参数的设置

DATABASE_DIR = path.realpath(__file__). \
    replace('pgportfolio/constants.pyc', '/database/Data.db'). \
    replace("pgportfolio\\constants.pyc", "database\\Data.db"). \
    replace('pgportfolio/constants.py', '/database/Data.db'). \
    replace("pgportfolio\\constants.py", "database\\Data.db")

CONFIG_FILE_DIR = 'net_config.json'
LAMBDA = 1e-4  # lambda in loss function 5 in training
# About time
NOW = 0
FIVE_MINUTES = 60 * 5
FIFTEEN_MINUTES = FIVE_MINUTES * 3
HALF_HOUR = FIFTEEN_MINUTES * 2
HOUR = HALF_HOUR * 2
TWO_HOUR = HOUR * 2
FOUR_HOUR = HOUR * 4
DAY = HOUR * 24
YEAR = DAY * 365
# trading table name
TABLE_NAME = 'test'

# initial btc value
INIT_BTC = 0.02

# trade coins
TRADE_COINS = ['ETH', 'EOS', 'XRP', 'ATOM', 'LTC', 'ETC', 'XMR', 'DASH', 'ZEC', 'BCHABC', 'BAT']

# coins trade amount precision
COINS_PRECISION = {'eth': 4, 'xrp': 0, 'bch': 4, 'ltc': 4, 'etc': 4, 'eos': 2, 'atom': 2, 'zec': 4, 'dash': 4, 'xmr': 4,
                   'bat': 0}
