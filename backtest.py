# -*- coding: utf-8 -*-

# 201118更新：移除了SignalEvent，Strategy直接生成OrderEvent到Broker
# 201119更新：优化了analysis的计算以避免异常，修复了回撤为0时报错的问题
# 201120更新：增加了symbol_start和symbol_update两项，以在股票未上市时填充数据

# 未解决问题1：如果在同一天内买卖调仓，卖出的资金无法及时反映到portfolio的cash
# 导致买入时可用的cash不足，需要考虑如何及时更新cash？流程先卖后买？
# 1. 队列只能FIFO或LIFO，不能插入；使用PriorityQueue队列？设置卖出优先级最高？
# 2. 将SELL和BUY区分为不同事件，中间插入update_portfolio？
# 核心问题在于，买卖同时出现在handlebar，导致portfolio几乎没办法实时更新。

import queue

import data
import strategy
import portfolio
import broker
import analysis
import ordertype

import tushare as ts

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

    def __init__(self,csv_dir,ContextInfo,Strategy):
        self.csv_dir = csv_dir
        self.Strategy = Strategy
        self.ContextInfo = ContextInfo

    # 执行回测
    def run(self):
        event_queue = queue.Queue() # 创建事件队列

        # 初始化行情数据、持仓列表、交易策略、交易记录
        bars = data.HistoricDataHandler(event_queue,self.csv_dir,self.ContextInfo)
        port = portfolio.Portfolio(event_queue,self.ContextInfo,bars)
        order = ordertype.Order(event_queue,bars,port) # 提供便捷的交易函数，不涉及主循环
        stg = self.Strategy(event_queue,self.ContextInfo,bars,port,order)
        brok = broker.SimulatedExecution(event_queue,self.ContextInfo,bars,port)

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

    # 导出回测数据
    def download_data(self):
        self.portfolios.download_portfolios()
        self.broker.download_records()

    # 生成绩效分析
    def get_performance(self):
        analysis.output_performance(self.portfolios,self.csv_dir,self.ContextInfo.benchmark)
        analysis.draw_plot(self.portfolios,self.csv_dir,self.ContextInfo.benchmark)

# 使用沪深300股票池
'''
sym_list = list(ts.get_hs300s()['code'])
sym_pool = []
for sym in sym_list:
    if sym.startswith('6'):
        ss = sym+'.SH'
    else:
        ss = sym+'.SZ'
    sym_pool.append(ss)
'''
sym_pool = ['600030.SH','000001.SZ','600999.SH']
#sym_pool = ['002736.SZ','600999.SH','688001.SH']
#sym_pool = ['600999.SH']

# 设置回测：股票池、基准、回测起止时间
# 默认初始资金1000000，佣金率0.0003，最低佣金5元
dict_CI = {"symbol_list":sym_pool,
           'benchmark':'399300.SZ',
           'start_date':'2018-01-01',
           'end_date':'2020-05-01',
           'initial_capital':1000000,
           'commission_rate':0.0003,
           'min_commission':5}

bt1 = backtest('D:/PYTHON/py_bt/sym_data',ContextInfo(dict_CI),strategy.SimpleMovingAverage)
#bt1 = backtest('D:/PYTHON/py_bt/sym_data',ContextInfo(dict_CI),strategy.MachineLearning)
bt1.run()
bt1.download_data()
bt1.get_performance()