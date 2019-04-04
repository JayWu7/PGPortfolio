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
        * 下载数据出现bug，应该是代码的问题，在思考修改方式
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

***
## 7. 根据训练结果执行交易：
       在 trader.py 中有个  trade_by_strategy() 函数
       backtest.py 继承并实现了这个函数

