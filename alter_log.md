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
## 3.增长训练区
   * 测试区间 `[2015/03/01 , 2015/12/28]`
        下载数据出现bug，应该是代码的问题，在思考修改方式
        ```ValueError: Must have equal len keys and value when setting with an iterable```
