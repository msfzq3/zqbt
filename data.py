# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
import pandas as pd
import os

from event import MarketEvent

class DataHandler(object):
    """
    DataHandler是一个抽象基类，提供所有后续的数据处理类的接口（包括历史和实际数据处理）
    数据处理对象的目标是输出一组针对每个请求的代码的数据条（OHLCVI）
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_latest_bar(self, symbol):
        """
        返回最近更新的数据条目
        """
        raise NotImplementedError("Should implement get_latest_bar()")

    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        """
        返回最近的N条数据
        """
        raise NotImplementedError("Should implement get_latest_bars()")

    @abstractmethod
    def update_bars(self):
        """
        将最近的数据条目放入到数据序列中，采用元组的格式
        (datetime,open,high,low,close,volume,open interest)
        """
        raise NotImplementedError("Should implement update_bars()")

class HistoricDataHandler(DataHandler):
    """
    HistoricDataHandler类用来读取请求的代码的历史行情数据
    历史行情数据以CSV文件形式存储在磁盘上。
    """

    def __init__(self, events, csv_dir, ContextInfo):
        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = ContextInfo.symbol_list
        self.benchmark = ContextInfo.benchmark
        self.start_date = ContextInfo.start_date
        self.end_date = ContextInfo.end_date

        self.full_list = self.symbol_list+[self.benchmark] # 代码列表+基准
        self.continue_backtest = True

        # Dictionary形式储存数据，Key为Symbol，Value为对应的DataFrame
        # symbol_data：回测期间的数据，起止时间为回测的start_date及end_date
        self.symbol_data = {}
        # symbol_start：每只股票在回测期间的最早数据日期
        self.symbol_start = {}
        # symbol_update：每只股票是否可以开始取数
        self.symbol_update = {}
        # latest_symbol_data：随着回测进行不断更新，可获取的全部数据
        # 起始时间为对应数据的最早时间，终止时间为回测进行的当前时间
        self.latest_symbol_data = {}
        # 用于间断遍历获取数据的generator
        self.data_generator = {}

        self.read_csv_files() # 数据初始化

    def read_csv_files(self):
        """
        从数据路径中打开CSV文件，转换为DataFrame
        """
        for sym in self.full_list:
            try:
                df = pd.read_csv(os.path.join(self.csv_dir,'%s.csv'%sym),encoding="gbk")
            except:
                print("%s is not available in the historical data set"%sym)
                break

            # 根据回测起止日期，对DataFrame进行切片
            df_bt = df[(df['date_time']>=self.start_date)&(df['date_time']<=self.end_date)]
            self.symbol_data[sym] = df_bt.reset_index(drop=True)

            # 获取DataFrame在回测起始日期之前的所有数据
            df_latest = df[df['date_time']<=self.start_date]
            self.latest_symbol_data[sym] = df_latest.reset_index(drop=True)
            # 创建generator以间断取数
            self.data_generator[sym] = self.symbol_data[sym].iterrows()

            # 检测数据是否可用
            try: # 获取sym在回测期间的最早日期
                self.symbol_start[sym] = df_bt.iloc[0]['date_time']
            except: # 如果获取不到，表明回测期间还没有上市，不参与回测
                self.symbol_start[sym] = 'unquoted'
            # 判断是否开始取数，默认设为关闭
            self.symbol_update[sym] = False

    def get_next_bar(self, sym):
        """
        从数据集返回新的数据条目
        """
        for bar in self.data_generator[sym]:
            yield bar # 通过generator实现数据的间断获取

    def update_bars(self):
        """
        将最近的数据条目放入到latest_symbol_data结构中。
        """

        try:
            # 获取最新的基准数据，格式为Dictionary
            bar_benchmark = dict(next(self.get_next_bar(self.benchmark))[1])
            # 将最新的基准bar写入latest_symbol_data
            self.latest_symbol_data[self.benchmark] = self.latest_symbol_data[self.benchmark].append(bar_benchmark,ignore_index=True)
            unnamed = self.latest_symbol_data[self.benchmark].iloc[-1]['Unnamed: 0']
            datetime = self.latest_symbol_data[self.benchmark].iloc[-1]['date_time']

            # 获取股票池数据
            for sym in self.symbol_list:
                # 判断sym数据起始日期是否与回测当前日期一致
                if self.symbol_start[sym] == self.latest_symbol_data[self.benchmark].iloc[-1]['date_time']:
                    self.symbol_update[sym] = True # 如果日期一致，则可以开始取数

                # 如果可以取数，则获取新的bar；否则根据基准日期填充数据
                if self.symbol_update[sym]:
                    bar = dict(next(self.get_next_bar(sym))[1])
                else:
                    bar = {'Unnamed: 0':unnamed,'date_time':datetime,
                           'symbol':sym,'name':'未上市',
                           'open':0,'low':0,'high':0,'close':0,'chg':0,'pct_chg':0,
                           'volume':0,'turnover':0,'suspend':True
                    }
                # 将最新的股票bar写入写入latest_symbol_data
                self.latest_symbol_data[sym] = self.latest_symbol_data[sym].append(bar,ignore_index=True)
                #print(self.latest_symbol_data[sym].iloc[-1])
            self.events.put(MarketEvent()) # 写入市场事件
        except StopIteration: # 获取不到数据，循环终止，停止回测
            self.continue_backtest = False

    def get_latest_bar(self, sym):
        """
        从最新的symbol_list中返回最新数据条目
        """
        try: # 返回latest_symbol_data的最后一行
            return self.latest_symbol_data[sym].iloc[-1]
        except KeyError:
            print("%s is not available in the historical data set"%sym)

    def get_latest_bars(self, sym, N=1):
        """
        从最新的symbol_list中返回最新数据条目
        """
        try: # 返回latest_symbol_data的倒数N行
            return self.latest_symbol_data[sym].iloc[-N:]
        except KeyError:
            print("%s is not available in the historical data set"%sym)

    def is_suspended_stock(self, sym):
        """
        确认股票是否为停牌状态
        """
        try: # 返回latest_symbol_data的最后一行
            return self.latest_symbol_data[sym].iloc[-1]['suspend']
        except KeyError:
            print("%s is not available in the historical data set"%sym)