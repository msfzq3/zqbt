# -*- coding: utf-8 -*-

from event import OrderEvent

# 设计一些委托单类型函数，方便策略中的下单操作
# 仅在Strategy中使用，不参与到具体的事件循环
# 优化：使用order类，直接加载bars、symbol、events，减少交易函数输入

class Order(object):

    def __init__(self,events, bars, portfolio):
        self.events = events
        self.bars = bars
        self.portfolio = portfolio

    # 按委托数量下单，不填价格则默认为市价单
    def order_share(self, symbol, qty, price='MARKET'):
        if price == 'MARKET':  # 市价单则委托价为收盘价
            price = self.bars.get_latest_bar(symbol)['close']
        if abs(qty) >= 100:
            my_order = OrderEvent(symbol, qty, price)
            self.events.put(my_order)

    # 按委托总额下单，不填价格则默认为市价单
    def order_value(self, symbol, value, price='MARKET'):
        if price == 'MARKET':  # 市价单则委托价为收盘价
            price = self.bars.get_latest_bar(symbol)['close']
        qty = value / price  # 计算委托数量
        if abs(qty) >= 100:
            my_order = OrderEvent(symbol, qty, price)
            self.events.put(my_order)

    # 按委托的目标金额下单，需要提供持仓信息，不填价格则默认为市价单
    def order_target_value(self, symbol, target_value, price='MARKET'):
        cur_hold = self.portfolio.holdings[symbol] # 获取当前市值
        value = target_value-cur_hold # 计算市值差额
        if price == 'MARKET': # 市价单则委托价为收盘价
            price = self.bars.get_latest_bar(symbol)['close']
        qty = value/price # 计算委托数量
        if abs(qty) >= 100:
            my_order = OrderEvent(symbol, qty, price)
            self.events.put(my_order)

    # 按委托的目标数量下单，需要提供持仓信息，不填价格则默认为市价单
    def order_target_share(self, symbol, target_share, price='MARKET'):
        cur_pos = self.portfolio.positions[symbol] # 获取当前持仓
        if price == 'MARKET': # 市价单则委托价为收盘价
            price = self.bars.get_latest_bar(symbol)['close']
        qty = target_share-cur_pos # 计算委托数量
        if abs(qty) >= 100:
            my_order = OrderEvent(symbol, qty, price)
            self.events.put(my_order)
    '''
# 按委托数量下单，不填价格则默认为市价单
def order_share(events, bars, symbol, qty, price='MARKET'):
    if price == 'MARKET': # 市价单则委托价为收盘价
        price = bars.get_latest_bar(symbol)['close']
    my_order = OrderEvent(symbol, qty, price)
    events.put(my_order)

# 按委托总额下单，不填价格则默认为市价单
def order_value(events, bars, symbol, value, price='MARKET'):
    if price == 'MARKET': # 市价单则委托价为收盘价
        price = bars.get_latest_bar(symbol)['close']
    qty = value/price  # 计算委托数量
    my_order = OrderEvent(symbol, qty, price)
    events.put(my_order)

# 按委托的目标金额下单，需要提供持仓信息，不填价格则默认为市价单
def order_target_value(events, bars, portfolio, symbol, target_value, price='MARKET'):
    cur_hold = portfolio.holdings[symbol] # 获取当前市值
    value = target_value-cur_hold # 计算市值差额
    if price == 'MARKET': # 市价单则委托价为收盘价
        price = bars.get_latest_bar(symbol)['close']
    qty = value/price # 计算委托数量
    my_order = OrderEvent(symbol, qty, price)
    events.put(my_order)

# 按委托的目标数量下单，需要提供持仓信息，不填价格则默认为市价单
def order_target_share(events, bars, portfolio, symbol, target_share, price='MARKET'):
    cur_pos = portfolio.positions[symbol] # 获取当前持仓
    if price == 'MARKET': # 市价单则委托价为收盘价
        price = bars.get_latest_bar(symbol)['close']
    qty = target_share-cur_pos # 计算委托数量
    my_order = OrderEvent(symbol, qty, price)
    events.put(my_order)
'''