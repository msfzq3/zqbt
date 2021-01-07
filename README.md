# zqbt
Event-Driven Backtester with Python

201118更新：移除了SignalEvent，Strategy直接生成OrderEvent到Broker
201119更新：优化了analysis的计算以避免异常，修复了回撤为0时报错的问题
201120更新：增加了symbol_start和symbol_update两项，以在股票未上市时填充数据
201224更新：增加了基本面数据——主要财务指标（mfi）及申万行业分类（swclass）
201225更新：在策略分类中增加了initialize()函数定义，用于设置额外的全局变量
201229更新：修复了基准回测出现数据重复读取的问题

210107更新：回测数据结构由DataFrame-Append结构优化为List-Dict封装结构，实测回测效率提高3倍
DataFrame结构handlebar耗时0.03s-0.05s；List结构handlebar耗时可忽略，但initialize耗时较长
测试2020.1-2020.7区间，多股均线策略，List结构耗时9.56秒，DataFrame结构耗时10.81秒
测试2015.1-2020.7区间，多股均线策略，List结构耗时56.49秒，DataFrame结构耗时101.06秒
进一步优化数据结构：1.portfolio持仓及市值列表；2.broker交易流水记录
测试2015.1-2020.7区间，多股均线策略，优化1耗时47.26秒，优化1+2耗时36.11秒
