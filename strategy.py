# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod

import ordertype
import pandas as pd
import numpy as np

class Strategy(object):
    """
    定义Strategy的基类
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, events, ContextInfo, bars, portfolio, order):
        self.events = events
        self.bars = bars
        self.portfolio = portfolio
        self.order = order
        self.symbol_list = ContextInfo.symbol_list
        self.benchmark = ContextInfo.benchmark
        self.start_date = ContextInfo.start_date
        self.end_date = ContextInfo.end_date
        self.initial_capital = ContextInfo.initial_capital
        self.commission_rate = ContextInfo.commission_rate

    @abstractmethod
    def initialize(self):
        """
        用于策略初始化的函数，可添加策略全局变量
        """
        raise NotImplementedError("Should implement initialize()")

    @abstractmethod
    def handlebar(self, event):
        """
        用于处理当前bar数据的函数
        """
        self.events = event
        raise NotImplementedError("Should implement handlebar()")

class SimpleMovingAverage(Strategy):
    """
    一个用于测试的简易多股均线策略，10日均线>30日均线买入，反之卖出
    """
    def initialize(self):
        return

    def handlebar(self, event):
        self.event = event
        #print(self.bars.get_latest_bar(self.symbol_list[0])['date_time'])
        print('[均线策略]日期:',self.portfolio.positions['date_time'])

        pos_list = self.portfolio.get_positions()

        # 生成调仓列表
        list_change = False
        for sym in self.bars.symbol_list:
            name = self.bars.get_latest_bar(sym)['name']
            ma_10 = self.bars.get_latest_bars(sym,10)['close'].mean()
            ma_30 = self.bars.get_latest_bars(sym,30)['close'].mean()

            if (ma_10 > ma_30) and (sym not in pos_list):
                print("[买入信号] Name:",name,"MA10:",ma_10,"MA30:",ma_30)
                pos_list.append(sym)
                list_change = True

            if (ma_10 < ma_30) and (sym in pos_list):
                print("[卖出信号] Name:",name,"MA10:",ma_10, "MA30:",ma_30)
                pos_list.remove(sym)
                list_change = True

        print('选股列表：',pos_list)
        # 如果列表变化，进行调仓
        if list_change:
            # 对不在列表的持仓股票执行卖出
            for sym in self.portfolio.get_positions():
                if sym not in pos_list:
                    #print(sym,self.portfolio.get_position(sym))
                    # ordertype.order_target_share(self.events,self.bars,self.portfolio,sym,0)
                    self.order.order_target_share(sym, 0)
            # 对列表内的股票，按总资产执行等额调仓
            if pos_list != []:
                count = len(pos_list)
                tar_value = self.portfolio.get_mkv()/count
                #print('每只股票买入：',tar_value)
                for sym in pos_list:
                    #ordertype.order_target_value(self.events,self.bars,self.portfolio,sym,tar_value)
                    self.order.order_target_value(sym,tar_value)

class MachineLearning(Strategy):
    """
    一个简易的机器学习策略：
    （1）用过去500天的单股历史价量数据训练模型，预测明天的收益率
    （2）预测收益率>1买入，预测收益率<1卖出，每5天进行一次调仓
    """
    def initialize(self):
        self.day_count = 0 # 用于设定调仓间隔
        return

    def handlebar(self, event):
        from sklearn.ensemble import RandomForestRegressor

        self.event = event
        #print(self.bars.get_latest_bar(self.symbol_list[0])['date_time'])
        #print(self.portfolio.positions['date_time'])

        # 单股模型，仅使用列表第一支股票
        sym = self.bars.symbol_list[0]

        pos = self.portfolio.get_position(sym)
        cash = self.portfolio.get_cash()
        name = self.bars.get_latest_bar(sym)['name']

        # 注意：未对数据做标准化处理，可能产生较大影响

        # 训练模型：X为前日pct_chg和volume，Y为当日的pct_chg
        his_data = self.bars.get_latest_bars(sym,500)
        pct_chg_train = list(his_data['pct_chg'][:-1])
        turn_rate_train = list(his_data['turn_rate'][:-1])
        volume_train = list(his_data['volume'][:-1])
        X_train = pd.DataFrame({'pct_chg':pct_chg_train,'volume':volume_train,'turn_rate':turn_rate_train})
        y_train = list(his_data['pct_chg'][1:])
        # 拟合模型，简单决策树
        model = RandomForestRegressor()
        model.fit(X_train,y_train)
        # 预测模型，基于当日pct_chg和volume
        X_pred = pd.DataFrame({'pct_chg':[pct_chg_train[-1]],'volume':[volume_train[-1]],'turn_rate':[turn_rate_train[-1]]})
        y_pred = model.predict(X_pred)[0]
        print("预测收益率：",y_pred,"前日实际收益率：",y_train[-1])

        # 每隔5天调仓，预测收益率>1%则买入，预测收益率<-1则卖出
        if y_pred > 1 and pos == 0 and self.day_count%5 == 0:
            print("[买入信号] Name:",name,"Predict Returns:",y_pred)
            self.order.order_target_value(sym,cash)
        if y_pred < -1 and pos != 0 and self.day_count%5 == 0:
            print("[卖出信号] Name:",name,"Predict Returns:",y_pred)
            self.order.order_target_share(sym,0)

        self.day_count += 1 # 策略天数+1

class RSRS(Strategy):
    """
    RSRS量化择时策略（Resistance Support Relative Strength）：
    （1）取过去N日的单股历史最高价及最低价序列
    （2）将最高价及最低价序列进行OLS线性回归，计算斜率
    （3）取前M日的斜率时间序列，计算当日斜率所处位置的标准分z
    （4）将z与拟合方程的决定系数相乘，作为当日RSRS指标值
    """
    def initialize(self):
        from sklearn import linear_model

        # 单股模型，仅使用列表第一支股票
        sym = self.bars.symbol_list[0]

        # 计算初始的beta_list，求回测前200日每日的模型beta值，并生成序列
        self.beta_list = []
        his_data = self.bars.get_latest_bars(sym,500)
        for dt in his_data['date_time'][-200:]:
            #print(dt)
            # 数据获取：X为前200日每日最低价序列，y为前200日每日最高价序列
            y_train = his_data[his_data['date_time']<dt]['high'][-200:]
            X_train = his_data[his_data['date_time']<dt]['low'][-200:]
            # 拟合模型，OLS简单线性回归
            model = linear_model.LinearRegression()
            model.fit(X_train.values.reshape(-1,1),y_train)
            beta = model.coef_[0] # 计算模型斜率
            self.beta_list.append(beta)
        #print(len(self.beta_list))
        return

    def handlebar(self, event):
        from sklearn import linear_model
        from sklearn.metrics import r2_score

        self.event = event
        #print(self.bars.get_latest_bar(self.symbol_list[0])['date_time'])
        #print(self.portfolio.positions['date_time'])

        # 单股模型，仅使用列表第一支股票
        sym = self.bars.symbol_list[0]

        pos = self.portfolio.get_position(sym)
        cash = self.portfolio.get_cash()
        name = self.bars.get_latest_bar(sym)['name']

        # 数据获取：X为前200日每日最低价序列，y为前200日每日最高价序列
        his_data = self.bars.get_latest_bars(sym,200)
        y_train = his_data['high']
        X_train = his_data['low']
        #print(his_data[''])
        # 拟合模型，OLS简单线性回归
        model = linear_model.LinearRegression()
        model.fit(X_train.values.reshape(-1,1),y_train)
        beta = model.coef_[0] # 计算模型斜率
        r2 = model.score(X_train.values.reshape(-1,1),y_train)
        self.beta_list.append(beta)

        # 根据前100日的beta序列数据，计算标准分位数z
        sd = np.std(self.beta_list[-100:])
        m = np.mean(self.beta_list[-100:])
        z = r2*(beta-m)/sd

        # 当前z值大于0.9买入，当前z值小于0.9卖出
        if z > 0.9 and pos == 0:
            print("[买入信号] Name:",name,"Z-Score:",z)
            self.order.order_target_value(sym,cash)
        if z < -0.9 and pos != 0:
            print("[卖出信号] Name:",name,"Z-Score:",z)
            self.order.order_target_share(sym,0)