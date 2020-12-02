# -*- coding: utf-8 -*-

import pandas as pd

class Portfolio(object):
    """
    Portfolio类处理所有的持仓和市场价值，针对在每个时间点上的数据的情况
    Positions DataFrame存放一个用时间做索引的持仓数量
    Holdings DataFrame存放特定时间索引对应的每个代码的现金和总的市场持仓价值
    """

    def __init__(self, events, ContextInfo, bars):
        self.events = events
        self.bars = bars
        self.initial_capital = ContextInfo.initial_capital
        self.symbol_list = ContextInfo.symbol_list
        self.benchmark = ContextInfo.benchmark
        self.start_date = ContextInfo.start_date
        self.end_date = ContextInfo.end_date

        # 历史持仓/市值，格式为DataFrame
        self.all_positions = pd.DataFrame()
        self.all_holdings = pd.DataFrame()
        # 实时持仓/市值，格式为Dictionary
        self.positions = self.set_positions()
        self.holdings = self.set_holdings()
        #print(len(self.positions))

    def set_positions(self):
        """
        构造完整的持仓矩阵
        """
        pos = dict()
        pos['date_time'] = self.bars.start_date
        pos['cash'] = self.initial_capital
        for sym in self.symbol_list:
            pos[sym] = 0

        return pos # 返回一个Dict，包含日期、现金及代码持仓

    def set_holdings(self):
        """
        构造完整的市值矩阵
        """
        hold = dict()
        hold['date_time'] = self.bars.start_date
        hold['cash'] = self.initial_capital
        for sym in self.symbol_list:
            hold[sym] = 0
        hold['mkt_value'] = self.initial_capital

        return hold # 返回一个Dict，包含日期、现金及代码市值

    def update_portfolios(self):
        """
        在持仓列表当中根据当前持仓增加一行，反映最新的持仓情况
        """
        # 更新日期（以基准的日期序列为准）
        self.positions['date_time'] = self.bars.get_latest_bar(
            self.benchmark
        )['date_time']
        self.holdings['date_time'] = self.positions['date_time']

        # 更新当前市值
        self.holdings['cash'] = self.positions['cash']
        mkt_value = 0 # 持仓总市值
        for sym in self.symbol_list:
            self.holdings[sym] = self.bars.get_latest_bar(sym)['close']*self.positions[sym]
            mkt_value += self.holdings[sym]
        self.holdings['mkt_value'] = self.holdings['cash']+mkt_value

        self.all_positions = self.all_positions.append(self.positions,ignore_index=True)
        self.all_holdings = self.all_holdings.append(self.holdings,ignore_index=True)

    def update_fill(self, event):
        """
        在接收到Fill事件后，更新当前持仓
        """
        sym = event.symbol
        order_amount = event.order_amount
        order_price = event.order_price
        commission = event.commission

        self.positions['cash'] -= order_price*order_amount+commission
        self.positions[sym] += order_amount
        #print(self.positions)

    def download_portfolios(self):
        """
        导出回测期间每日的持股数及市值
        """
        df = pd.DataFrame()
        df['date_time'] = self.all_positions['date_time']
        df['cash'] = self.all_positions['cash']
        for sym in self.symbol_list:
            df['pos_'+sym] = self.all_positions[sym]
            df['mkv_'+sym] = self.all_holdings[sym]
        df['mkt_value'] = self.all_holdings['mkt_value']

        df.to_csv('portfolios_records.csv')

    def get_cash(self):
        """
        获取可用资金
        """
        return self.positions['cash']

    def get_position(self,sym):
        """
        获取单只股票的持仓数量
        """
        return self.positions[sym]