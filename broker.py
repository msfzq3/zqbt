# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
import pandas as pd

from event import FillEvent
import datetime

class ExecutionHandler(object, metaclass=ABCMeta):
    """
    ExecutionHandler抽象类处理由Portfolio生成的order对象
    与实际市场中发生的Fill对象之间的交互
    这个类可以用于实际的成交，或者模拟的成交
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def execute_order(self, event):
        """
        获取一个Order事件并执行，产生Fill事件放到事件队列中
        """
        raise NotImplementedError("Should implement execute_order()")

class SimulatedExecution(ExecutionHandler):
    """
    这是一个模拟的执行处理，简单的将所有的Order对象转化为等价的Fill对象
    不考虑时延，滑价以及成交比率的影响
    """

    def __init__(self, events, ContextInfo, bars, portfolio):
        self.events = events
        self.bars = bars
        self.portfolio = portfolio
        self.commission_rate = ContextInfo.commission_rate
        self.min_commission = ContextInfo.min_commission
        self.execution_records = pd.DataFrame(
            columns=['date_time','symbol','order_price','order_amount','commission'])

    def update_temp_pos(self):
        """
        做一个临时的持仓表，以判断现金和持仓是否充足可用（实盘由交易所判断）
        在Portfolio处理完FILL事件后，重新获取temp_pos
        """
        #print(self.portfolio.positions)
        self.temp_pos = {}
        self.temp_pos['cash'] = self.portfolio.positions['cash']
        for sym in self.portfolio.symbol_list:
            self.temp_pos[sym] = self.portfolio.positions[sym]
        #print(self.temp_pos)
        #print(len(self.temp_pos))

    def execute_order(self, event):
        """
        接收Order事件，生成Fill事件
        """
        symbol = event.symbol
        order_amount = event.order_amount
        order_price = event.order_price

        cur_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        bar_date = self.bars.get_latest_bar(symbol)['date_time']
        last_close = self.bars.get_latest_bar(symbol)['close']

        # 判断是否停牌
        if self.bars.is_suspended_stock(symbol):
            print("[%s]Time：%s，Symbol：%s，Stock Suspended！"%(cur_date,bar_date,symbol))
            return

        # 市价单：委托价为收盘价
        if order_price == 'MARKET':
            order_price = last_close

        # 股价判断：买入/卖出价若低于/高于收盘价，则按收盘价执行
        if order_amount < 0 and order_price > last_close:
            order_price = last_close
        if order_amount > 0 and order_price < last_close:
            order_price = last_close

        # 处理order_amount，向下取整百
        order_amount = int(order_amount/100)*100
        if order_amount == 0: # 委托数量为0，则中止运行
            print("[%s][委托数量错误]Time：%s，Symbol：%s，Price：%s，Qty：%s，Quantity Error！"%(cur_date,bar_date,symbol,order_price,order_amount))
            return

        # 计算手续费=MAX（交易额*佣金率，最低手续费）
        commission = max(round(order_price*abs(order_amount)*self.commission_rate,2),self.min_commission)

        # 判断现金及持仓是否可用
        if order_amount > 0: # 若买入，判断可用资金
            if order_amount*order_price+commission > self.temp_pos['cash']:
                # 可用资金不足，不执行买入
                print("[%s][可用资金不足]Time：%s，Symbol：%s，Price：%s，Qty：%s，Cash Error！"%(cur_date,bar_date,symbol,order_price,order_amount))
                return
        elif order_amount < 0: # 若卖出，判断可用数量
            if order_amount < -self.temp_pos[symbol]:
                # 可用数量不足，拒绝执行卖出
                print("[%s][可用持仓不足]Time：%s，Symbol：%s，Price：%s，Qty：%s，Position Error！"%(cur_date,bar_date,symbol,order_price,order_amount))
                return

        # 交易撮合，生成FILL事件
        fill_event = FillEvent(symbol,order_amount,order_price,commission)
        self.events.put(fill_event)
        print("[%s][委托交易成功]Time：%s，Symbol：%s，Price：%s，Qty：%s"%(cur_date,bar_date,symbol,order_price,order_amount))

        # 实时更新至temp_pos，以便验证每个订单的持仓及金额是否可用
        # 此处遇到问题：如果直接令temp_pos=portfolio.positions，
        # 当temp_pos变动时，portfolio也会发生变动，
        # 而新建一个temp_pos字典可以解决这个问题，具体原因不明
        # print(self.portfolio.positions)
        self.temp_pos['cash'] -= order_price*order_amount+commission
        self.temp_pos[symbol] += order_amount
        # print(self.portfolio.positions)

        # 写入交易记录
        record = {}
        record['date_time'] = bar_date
        record['symbol'] = symbol
        record['order_price'] = order_price
        record['order_amount'] = order_amount
        record['commission'] = commission
        self.execution_records = self.execution_records.append(record, ignore_index=True)

    def download_records(self):
        """
        导出交易记录
        """
        self.execution_records.to_csv('execution_records.csv')