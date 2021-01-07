# -*- coding: utf-8 -*-

# 201118更新：移除了SignalEvent，Strategy直接生成OrderEvent到Broker
# 201119更新：优化了analysis的计算以避免异常，修复了回撤为0时报错的问题
# 201120更新：增加了symbol_start和symbol_update两项，以在股票未上市时填充数据
# 201224更新：增加了基本面数据——主要财务指标（mfi）及申万行业分类（swclass）
# 201225更新：在策略分类中增加了initialize()函数定义，用于设置额外的全局变量
# 201229更新：修复了基准回测出现数据重复读取的问题

# 210107更新：回测数据结构由DataFrame-Append结构优化为List-Dict封装结构，实测回测效率提高3倍
# DataFrame结构handlebar耗时0.03s-0.05s；List结构handlebar耗时可忽略，但initialize耗时较长
# 测试2020.1-2020.7区间，多股均线策略，List结构耗时9.56秒，DataFrame结构耗时10.81秒
# 测试2015.1-2020.7区间，多股均线策略，List结构耗时56.49秒，DataFrame结构耗时101.06秒
# 随着回测区间拉长，股票池数量增加，List-Dict结构优势将会更明显
# 进一步优化数据结构：1.portfolio持仓及市值列表；2.broker交易流水记录
# 测试2015.1-2020.7区间，多股均线策略，优化1耗时47.26秒，优化1+2耗时36.11秒

# 未解决问题1：如果在同一天内买卖调仓，卖出的资金无法及时反映到portfolio的cash
# 表现：执行handlebar后，同时生成一批OrderEvent，包含买入及卖出
# 只有全部Order处理完成后，才开始处理Fill（形式为Order-Order-Fill-Fill）
# 导致买入Order由于策略计算的cash不足而无法执行，实际Fill后cash是足够的
# 需要考虑如何实时更新cash？流程先卖后买？
# 1. 队列只能FIFO或LIFO，不能插入；使用PriorityQueue队列可设置Event优先级
# 用PriorityQueue可以实现：调高FillEvent优先级，使得Order处理后立刻处理Fill
# 通过timestamp+sleep的方式使每笔order时间错开，实现按时间顺序处理Order+Fill
# 形式改变为（Order-Fill-Order-Fill），这样处理Order时可以保证为实时数据
# 但是在handlebar中取得的cash依然是错误的，使用依然困难
# 2. 使用get_mkv取代get_cash
# 对调仓策略的临时解决方案，但灵活性不如get_cash

import queue
import data
import strategy
import portfolio
import broker
import analysis
import ordertype
import query
import tushare as ts
import time

class ContextInfo(object):
    """
    回测需要使用的基础参数
    """
    def __init__(self,dict):
        self.symbol_list = dict['symbol_list']
        self.benchmark = dict['benchmark']
        self.start_date = dict['start_date']
        self.end_date = dict['end_date']
        self.initial_capital = dict['initial_capital']
        self.commission_rate = dict['commission_rate']
        self.min_commission = dict['min_commission']

class backtest(object):

    def __init__(self,ContextInfo,Strategy):
        self.Strategy = Strategy
        self.ContextInfo = ContextInfo

    # 执行回测
    def run(self):
        self.t0 = time.time() # 回测起始时间
        event_queue = queue.Queue() # 创建事件队列
        #event_queue = queue.PriorityQueue() # 优先队列，用于FILL实时回填

        # 初始化行情数据、持仓列表、交易策略、交易记录
        bars = data.HistoricDataHandler(event_queue,self.ContextInfo)
        port = portfolio.Portfolio(event_queue,self.ContextInfo,bars)
        order = ordertype.Order(event_queue,bars,port) # 提供便捷的交易函数，不涉及主循环
        stg = self.Strategy(event_queue,self.ContextInfo,bars,port,order)
        brok = broker.SimulatedExecution(event_queue,self.ContextInfo,bars,port)
        stg.initialize() # 策略初始化函数
        print("[Initialized]Time:",time.time()-self.t0) # 初始化耗时

        # 事件驱动主循环
        while True:
            bars.update_bars()  # 获取新数据

            if bars.continue_backtest:
                port.update_portfolios()  # 更新持仓列表
                brok.update_temp_pos() # 更新broker的当前持仓（实盘不需要）
            else:
                break # 数据处理完毕，跳出外循环

            while True: # 处理新数据
                try:
                    event = event_queue.get(False) # 获取事件队列
                except queue.Empty: # 事件队列为空，跳出内循环
                    break

                else: # 处理新事件
                    if event is not None:
                        #print(event.type)
                        if event.type == 'MARKET': # 基于数据生成市场事件
                            stg.handlebar(event)

                        elif event.type == 'ORDER': # 基于策略生成委托事件
                            brok.execute_order(event)

                        elif event.type == 'FILL': # 基于成交生成回报事件
                            port.update_fill(event)

        # 回测结束，保存持仓及交易记录
        self.portfolios = port
        self.broker = brok
        print("[Backtest Finished]Time:",time.time()-self.t0) # 回测累计耗时

    # 导出回测数据
    def download_data(self):
        self.portfolios.download_portfolios()
        self.broker.download_records()

    # 生成绩效分析
    def get_performance(self):
        analysis.output_performance(self.portfolios,self.ContextInfo.benchmark)
        analysis.draw_plot(self.portfolios,self.ContextInfo.benchmark)
'''
# 使用沪深300股票池
sym_list = list(ts.get_hs300s()['code'])
sym_pool = []
for sym in sym_list:
    if sym.startswith('6'):
        ss = sym+'.SH'
    else:
        ss = sym+'.SZ'
    sym_pool.append(ss)
'''
# 注意股票池不能有重复代码，否则bar切片数据有误
#sym_pool = ['000568.SZ','002352.SZ','603259.SH','601318.SH','600030.SH',
#            '600036.SH','000333.SZ','601888.SH','600887.SH','000651.SZ',
#            '600276.SH','300059.SZ','300015.SZ']
#sym_pool = query.get_industry_stock('食品饮料')
#sym_pool = ['600519.SH','600030.SH','000001.SZ']
#sym_pool = ['600999.SH']
sym_pool = ['399300.SZ']

# 设置回测：股票池、基准、回测起止时间
# 默认初始资金1000000，佣金率0.0003，最低佣金5元
dict_CI = {"symbol_list":sym_pool,
           'benchmark':'399300.SZ',
           'start_date':'2005-01-01',
           'end_date':'2020-07-31',
           'initial_capital':10000000,
           'commission_rate':0.0003,
           'min_commission':5}

#bt1 = backtest(ContextInfo(dict_CI),strategy.SimpleMovingAverage)
#bt1 = backtest(ContextInfo(dict_CI),strategy.MachineLearning)
bt1 = backtest(ContextInfo(dict_CI),strategy.RSRS)
bt1.run()
bt1.download_data()
bt1.get_performance()