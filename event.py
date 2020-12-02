# -*- coding: utf-8 -*-

class Event(object):
    """
    Event的基类，提供所有后续子类的一个接口，在后续的交易系统中会触发进一步的事件
    """

    pass

class MarketEvent(Event):
    """
    市场数据更新，由DataHandler对象发出，被Strategy对象接收
    """

    def __init__(self):
        self.type = 'MARKET'

class OrderEvent(Event):
    """
    委托单提交，由Strategy对象发出，被ExecutionHandler对象接收
    """

    def __init__(self, symbol, order_amount, order_price='MARKET'):
        self.type = 'ORDER'
        self.symbol = symbol
        self.order_amount = order_amount
        self.order_price = order_price

class FillEvent(Event):
    """
    交易结果回报，由ExecutionHandler对象发出，被Portfolio对象接收
    """

    def __init__(self, symbol, order_amount, order_price, commission):
        self.type = 'FILL'
        self.symbol = symbol
        self.order_amount = order_amount
        self.order_price = order_price
        self.commission = commission