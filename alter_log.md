# 修改日志
***

## 1.手续费：

​	*PGportfolio*项目在 *net_config.json* 文件中设置了交易手续费，为: ***0.0025***
```json
        "trading": {
            "buffer_biased": 5e-05,
            "learning_rate": 0.00028,
            "rolling_training_steps": 85,
            "trading_consumption": 0.0025
        }	
```
***
## 2.调整训练时间段（period）：

​	以时间区间`[2019/01/01 , 2019/03/01]`训练的效果不明显  
    经过90000steps训练后，portfolio value 增长几乎为0.
  
   换用时间区间`[2019/02/01 , 2019/03/28]`，训练效果依然不佳
    
   使用原论文测试有效训练时间：`[2016/09/07 , 2016/10/28]`
   
    修改时间后，运行会出错：
        'error': 'Data requested is too large. Please specify a longer period or a shorter date range, or use resolution=auto to automatically calculate the shortest supported period for your date range.'
    初步判断是从api获取数据时出的问题`
    
    bug解决：
        当前数据库里有19年的数据，此时在线训练16年的数据，在globaldatamatrix.py中，
       有个 update_data 方法，会将修改后的end 和 period传入爬取数据的函数，从而导致抓取量过大，产生错误。
       ``self.__fill_data(start, min_date - self.__storage_period - 1, coin, cursor)``   #此句有问题
    
        解决方法：  暂时先将原有的Data.db 删除，在线下载数据
    
    解决bug后，训练效果有了一定提升，由 1.0 BTC -> 1.114864 BTC,但是和论文实验结果还是有很大差距。
    
  重新测试区间 `[2015/01/01, 2015/03/01]`:
  * 效果非常明显！
  * 由 1.0 BTC ->  7.456198 BTC
***
## 3.增长训练区间
   * 测试区间 `[2015/03/01 , 2015/12/28]`
        * 下载数据出现bug:
        ```ValueError: Must have equal len keys and value when setting with an iterable```
        * bug：  
          globaldatamatrix.py 中的第81行， sql语句中的 `300` 有误，应改为`period`  
        * 修改第81行代码为：  
          ` sql = ("SELECT date+{period} AS date_norm, close FROM History WHERE"  #此处将300改为period`  
        * 修改后，程序可以正常运行,但是训练效果很差：  
            ```
            the step is 1127  
            total assets are 1.000000 BTC
            ```
   * 测试区间 `[2015/07/01 , 2017/07/01]`  
    效果有，但不明显:  
           
        ```
        the step is 2775  
        total assets are 1.398338 BTC
        ```
   * 测试区间 `[2017/05/01 , 2018/05/01]`  
   效果非常差：
        ```
        the step is 1369
        total assets are 0.621370 BTC
        ```
   * 测试区间 `[2017/01/01 , 2017/11/28]`  
   有一点效果：
        ```
        the step is 1354
        total assets are 1.690218 BTC
        ```
   * 测试区间 `[2016/01/01 , 2017/01/01]`
   效果糟糕：
        ```
        the step is 1373
        total assets are 0.974707 BTC
        ```
          
***                 
## 4.调整训练参数：
* ### 训练方法：  
        * 1. GradientDescent  
        * 2. Adam (默认方法)
        * 3. RMSProp   
    具体代码见: **learn/nnagent.py** 中的 `init_train` 方法。
* ### 是否快速训练：
     * 在 **net_config.json** 中 设置 **fast_train** = [false or true]
     * 具体 fast_train 和 not fast_train 的区别见：
            _**rollingtrainer.py**_  中的： _**__rolling_logging**_ 方法

***
## 5. 输出总交易手续费：
   结束交易后，输出此时间段交易的总手续费。  
   修改代码：  
   * 1 在 _**trader.py**_ 中添加: **__calculate_total_commission_fee_** 方法
   * 2 在 **backtest.py** 中的 ***trade_by_strategy***方法 第 _79_ 行添加：
        `self._calculate_total_commission_fee(pv_after_commission, value_after_training)  # 计算累积commission`               
   * 3 在 **backtest.py** 中的 **_finish_trading_**方法 第 _36_ 行添加：
        `logging.info("Total commission cost is: {} {}".format(self._total_commission_cost,'BTC'))`
   * 4 输出结果
   ```
    the step is 3001
    total assets are 7.628891 BTC
    Total commission cost is: 2.7399826498251487 BTC
   ```
***       
## 6. 输出交易详细信息
在trader.py中添加了 _log_trade_detail 函数，并在backtest.py中实现了它:

```buildoutcfg
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
```

输出具体格式为：
```
the step is 371
  Selling 0.0032258535891411264 btc's BTC, the weight decreases from 0.006600779195176717 to 0.0034243809059262276
  Selling 0.0004171844029188331 btc's reversed_USDT, the weight decreases from 0.0005244516425463704 to 0.00011366305989213288
  Selling 0.004129913609985584 btc's LTC, the weight decreases from 0.004473122492973885 to 0.000406524253776297
  Selling 0.0005725732918422156 btc's ETH, the weight decreases from 0.0006856999870295666 to 0.0001219047699123621
  Selling 0.0005362307910579191 btc's XRP, the weight decreases from 0.0006335237366635554 to 0.00010551385639701039
  Selling 0.00045872997917973193 btc's reversed_USDC, the weight decreases from 0.0005843928532877593 to 0.0001326956262346357
  Selling 0.9833630604278185 btc's BCHABC, the weight decreases from 0.9820833368420274 to 0.013796135783195496
  Selling 0.0007079052083389664 btc's STR, the weight decreases from 0.0009281862904140868 to 0.0002311339194420725
  Selling 0.0008378759407920114 btc's XMR, the weight decreases from 0.0009360857947568807 to 0.00011105526209576055
  Selling 0.0016690755565798708 btc's DASH, the weight decreases from 0.001949417188843328 to 0.0003059300943277776
  Buying 0.9962765365160208 btc's BCHSV, the weight increases from 0.00011347395967079477 to 0.9811161756515503
  Selling 0.0003580259712771655 btc's ZEC, the weight decreases from 0.00048753593475015015 to 0.00013499883061740547
total assets are 1.050106 BTC
```

***
## 7. 根据训练结果执行交易：
       在 trader.py 中有个  trade_by_strategy() 函数
       backtest.py 继承并实现了这个函数

## 8. 核实能否实现做空：
       即核实能否判断出要下跌的股票

## 9. 生成Docker镜像：
        目前计划使用Ubuntu系统而不是Windows重新构建一个运行环境

***
## 10. 修改poloniex.py 
  增加了判断爬取超时机制，如果爬取一个json超过1分钟还未成功，则raise Exception  
  修改 api() 函数，修改后为：  
  ```
    def api(self, command, args={}):
        if command in PUBLIC_COMMANDS:
            url = 'https://poloniex.com/public?'
            args['command'] = command
            url = url + urlencode(args)
            try:
                self.conn = urlopen(Request(url), timeout=60)  # 60s没打开则超时
                json_str = json.loads(self.conn.read().decode(encoding='UTF-8'))
                if 'error' in json_str and len(json_str) == 1:
                    raise ValueError('Data requested is too large, url is {}'.format(url))
                return json_str
            except URLError:
                raise URLError('connect {} error!'.format(url))
        else:
            return False
```
***
## 11. 修改一个关键参数：
之前因为数据下载失败，将**_/pgportfolio/marketdata/globaldatamatrix.py_**中：
第20行的 **_self.__storage_period_** 修改成了 DAY （86400）
数据爬取问题解决后，修改为原来的 FIVE_MINUTES， 测试效果明显好转：

```buildoutcfg
the step is 194
total assets are 91.138219 BTC
Total commission cost is: 17.099172777243812 BTC
All the Tasks are Over,total time cost is 1335.0637793540955 s
```

***
## 12. 采用不同的训练方法，测试训练效果

训练区间： `[2015/01/01, 2015/03/01]`  训练步数： `8000`
* a. Adam:  (效果很好)
```buildoutcfg
the step is 194
total assets are 62.767655 BTC
Total commission cost is: 11.192812211441508 BTC
All the Tasks are Over,total time cost is 825.0877954959869 s
```
* b. GradientDescent: (效果堪忧)
```buildoutcfg
the step is 194
total assets are 1.009335 BTC
Total commission cost is: 0.009474774566169778 BTC
All the Tasks are Over,total time cost is 375.02694392204285 s
```

* c. RMSProp: (效果理想)
```buildoutcfg
the step is 194
total assets are 47.879087 BTC
Total commission cost is: 8.499764558195123 BTC
All the Tasks are Over,total time cost is 380.0338079929352 s
```
***
训练区间： `[2019/01/01, 2019/04/08]`  训练步数： `30000`

* a. Adam: (效果不错)
```buildoutcfg
the step is 340
total assets are 3.692637 BTC
Total commission cost is: 1.3877036983392497 BTC
All the Tasks are Over,total time cost is 1180.0701975822449 s
```
* b. GradientDescent: (效果堪忧)
```buildoutcfg
the step is 340
total assets are 1.002613 BTC
Total commission cost is: 0.006522101848995306 BTC
All the Tasks are Over,total time cost is 695.0470299720764 s
```

* c. RMSProp: (效果不错)
```buildoutcfg
the step is 340
total assets are 3.421211 BTC
Total commission cost is: 1.128473636940146 BTC
All the Tasks are Over,total time cost is 795.0882556438446 s
```

***
训练区间： `[2018/10/01, 2019/03/01]`  训练步数： `30000`
* a. Adam: (效果不错)
```buildoutcfg
the step is 547
total assets are 2.560543 BTC
Total commission cost is: 2.560890037149945 BTC
All the Tasks are Over,total time cost is 900.0495800971985 s
```

* b. GradientDescent: (效果不好)
```buildoutcfg
the step is 547
total assets are 0.983031 BTC
Total commission cost is: 0.00715608017340627 BTC
All the Tasks are Over,total time cost is 1340.1400792598724 s
```

* c. RMSProp: (效果理想)
```buildoutcfg
total assets are 2.825635 BTC
the step is 547
total assets are 2.825235 BTC
Total commission cost is: 1.4786406733220454 BTC
All the Tasks are Over,total time cost is 1000.1118497848511 s
```

继续测试此区间，更换测试steps，方法使用 Adam 和 RMSProp：

1. 50000 steps， Adam：
```buildoutcfg
the step is 547
total assets are 2.846247 BTC
Total commission cost is: 2.926565633324409 BTC
All the Tasks are Over,total time cost is 1650.152584552765 s
```

2. 50000 steps， RMSProp：
```buildoutcfg
the step is 547
total assets are 3.070942 BTC
Total commission cost is: 1.6703643707968703 BTC
All the Tasks are Over,total time cost is 7108.959946870804 s
```

更换训练次数至 80000 steps：

Adam：
```buildoutcfg
the step is 547
total assets are 2.993143 BTC
Total commission cost is: 2.940805687719876 BTC
All the Tasks are Over,total time cost is 2485.4244163036346 s
```

RMSProp:
```buildoutcfg
the step is 547
total assets are 3.266608 BTC
Total commission cost is: 1.7923864193707273 BTC
All the Tasks are Over,total time cost is 39063.200154304504 s
```

更换训练步数至 100000 steps：

Adam：
```buildoutcfg
the step is 547
total assets are 3.052300 BTC
Total commission cost is: 2.9244506845837797 BTC
All the Tasks are Over,total time cost is 2255.311032772064 s
```

RMSProp:
```buildoutcfg
the step is 547
total assets are 3.329421 BTC
Total commission cost is: 1.8063832642471864 BTC
All the Tasks are Over,total time cost is 1675.2352316379547 s
```

***
训练区间 [2017/03/01, 2019/03/01]

steps 3000:

Adam:
```buildoutcfg
the step is 2771
total assets are 248.239861 BTC
Total commission cost is: 186.99646694694266 BTC
All the Tasks are Over,total time cost is 2220.0452315807343 s
```
RMSProp:
```buildoutcfg
the step is 2771
total assets are 201.961743 BTC
Total commission cost is: 160.1141332048935 BTC
All the Tasks are Over,total time cost is 2495.984961748123 s
```

steps 30000:

Adam
```buildoutcfg
the step is 2771
total assets are 573.154686 BTC
Total commission cost is: 433.6781422970878 BTC
All the Tasks are Over,total time cost is 2220.0380775928497 s
```

RMSProp:
```buildoutcfg
the step is 2771
total assets are 388.794596 BTC
Total commission cost is: 306.5773426398393 BTC
All the Tasks are Over,total time cost is 2525.045242547989 s
```


***
## 13. 交易步数 steps
和 _训练步数_ 无关  
与 _时间区间_ 的 _长度_ 成正比