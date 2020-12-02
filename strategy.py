# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod

import ordertype

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
        self.day_count = 0 # 用于设定调仓间隔

    @abstractmethod
    def handlebar(self, event):
        """
        返回最近更新的数据条目
        """
        self.events = event
        raise NotImplementedError("Should implement handlebar()")

class SimpleMovingAverage(Strategy):
    """
    一个用于测试的简易均线策略，10日均线>30日均线买入，反之卖出
    """

    def handlebar(self, event):
        self.event = event
        #print(self.bars.get_latest_bar(self.symbol_list[0])['date_time'])
        #print(self.portfolio.positions['date_time'])

        buy_list = []
        sell_list = []
        # 生成买入及卖出列表
        for sym in self.bars.symbol_list:
            pos = self.portfolio.get_position(sym)

            name = self.bars.get_latest_bar(sym)['name']
            ma_10 = self.bars.get_latest_bars(sym,10)['close'].mean()
            ma_30 = self.bars.get_latest_bars(sym,30)['close'].mean()

            if ma_10 > ma_30 and pos == 0 and not self.bars.is_suspended_stock(sym):
                print("[买入信号] Name:",name,"MA10:",ma_10,"MA30:",ma_30)
                buy_list.append(sym)

            if ma_10 < ma_30 and pos != 0 and not self.bars.is_suspended_stock(sym):
                print("[卖出信号] Name:",name,"MA10:",ma_10, "MA30:",ma_30)
                sell_list.append(sym)

        # 对卖出列表的股票执行卖出
        for sym in sell_list:
            #ordertype.order_target_share(self.events,self.bars,self.portfolio,sym,0)
            self.order.order_target_share(sym,0)

        # 对买入列表的股票执行等额买入
        if buy_list != []:
            count = len(buy_list)
            tar_value = self.portfolio.get_cash()/count
            for sym in buy_list:
                #ordertype.order_target_value(self.events,self.bars,self.portfolio,sym,tar_value)
                self.order.order_target_value(sym,tar_value)

class MachineLearning(Strategy):
    """
    一个简易的机器学习策略：
    （1）用过去500天的单股历史价量数据训练模型，预测明天的收益率
    （2）预测收益率>0买入，预测收益率<0卖出，每3天进行一次调仓
    """

    def handlebar(self, event):
        import pandas as pd
        from sklearn.tree import DecisionTreeRegressor

        self.event = event
        #print(self.bars.get_latest_bar(self.symbol_list[0])['date_time'])
        #print(self.portfolio.positions['date_time'])

        # 单股模型，仅使用列表第一支股票
        sym = self.bars.symbol_list[0]

        pos = self.portfolio.get_position(sym)
        cash = self.portfolio.get_cash()
        name = self.bars.get_latest_bar(sym)['name']

        # 注意：未对数据做标准化处理，影响可能比较大！

        # 训练模型：X为前日pct_chg和volume，Y为当日的pct_chg
        his_data = self.bars.get_latest_bars(sym,500)
        pct_chg_train = list(his_data['pct_chg'][:-1])
        volume_train = list(his_data['volume'][:-1])
        X_train = pd.DataFrame({'pct_chg':pct_chg_train,'volume':volume_train})
        y_train = list(his_data['pct_chg'][1:])
        # 拟合模型，简单决策树
        model = DecisionTreeRegressor()
        model.fit(X_train,y_train)
        # 预测模型，基于当日pct_chg和volume
        X_pred = pd.DataFrame({'pct_chg':[pct_chg_train[-1]],'volume':[volume_train[-1]]})
        y_pred = model.predict(X_pred)[0]
        #print("预测收益率：",y_pred)

        # 每隔3天调仓，预测收益率>0则买入，预测收益率<0则卖出
        if y_pred > 0 and pos == 0 and self.day_count%3 == 0:
            print("[买入信号] Name:",name,"Predict Returns:",y_pred)
            self.order.order_target_value(sym,cash)
        if y_pred < 0 and pos != 0 and self.day_count%3 == 0:
            print("[卖出信号] Name:",name,"Predict Returns:",y_pred)
            self.order.order_target_value(sym,0)

        self.day_count += 1 # 策略天数+1
