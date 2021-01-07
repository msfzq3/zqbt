# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
import pandas as pd
import os

# 提供股票数据的综合查询，包括基本面数据、行业数据等
# 仅在Strategy中使用，不参与到具体的事件循环

# 优化：直接init加载所有symbol_list的基本面数据至dict，后续可读取

# 获取个股所属行业（申万分类）
def get_industry(symbol):
    df = pd.read_csv('database/swclass.csv',encoding="gbk")
    return(df[df['symbol']==symbol]['industry'].values[0])

# 获取行业成分股（申万分类）
def get_industry_stock(industry):
    df = pd.read_csv('database/swclass.csv',encoding="gbk")
    #return (df[df['industry'] == industry].reset_index(drop=True))
    return(list(df[df['industry']==industry]['symbol']))

# 获取个股EPS
def get_eps(symbol):
    df = pd.read_csv('database/mfi_data/%s.csv'%symbol,encoding="gbk")
    return(df[['post_date','eps']])

# 获取个股ROC
def get_roc(symbol):
    df = pd.read_csv('database/mfi_data/%s.csv'%symbol,encoding="gbk")
    return(df[['post_date','roc']])

'''
class MainFinancialIndex(object):
    """
    MainFinancialIndex类用来读取请求的代码的财务指标数据
    财务指标数据以CSV文件形式存储在磁盘上。
    """
    def __init__(self, ContextInfo):
        self.symbol_list = ContextInfo.symbol_list
        self.benchmark = ContextInfo.benchmark

        self.full_list = self.symbol_list+[self.benchmark] # 代码列表+基准
        #self.full_list = self.symbol_list

        # Dictionary形式储存数据，Key为Symbol，Value为对应的DataFrame
        self.mfi_data = {}

        self.read_csv_files() # 数据初始化

    def read_csv_files(self):
        """
        从数据路径中打开CSV文件，转换为DataFrame
        """
        for sym in self.full_list:
            try:
                df = pd.read_csv('database/mfi_data/%s.csv'%sym,encoding="gbk")
                self.mfi_data[sym] = df.reset_index(drop=True)
            except:
                print("%s is not available in the main financial index data set"%sym)

    def get_eps(self,symbol):
        df = self.mfi_data[symbol]
        #df = df[df['post_date'] <= end_date]
        return(df[['post_date','eps']])
'''