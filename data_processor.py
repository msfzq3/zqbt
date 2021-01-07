# -*- coding: utf-8 -*-

"""
处理网易财经爬取的原始数据，不涉及回测框架
"""

import pandas as pd
import os
import re

# 处理原始历史数据
# 注意：399300.SZ的市值、换手率字段不存在，需要另外填充
li_all_sym = os.listdir('database/sym_data_raw')

# 只处理未创建的数据
#li_exist_sym = os.listdir('sym_data')
#for sym in li_all_sym:
#    if sym in li_exist_sym:
#        li_all_sym.remove(sym)

li_failed = []
for fn in li_all_sym:
    sym = re.split('.csv', fn)[0]
    print('处理中：',sym)
    try:
        df = pd.read_csv('database/sym_data_raw/%s.csv'%sym,encoding='gbk')

        # 整理到新数据表df_new
        df_new = pd.DataFrame()
        df_new['date_time'] = df['日期']
        df_new['symbol'] = sym
        df_new['name'] = df['名称']
        df_new['open'] = df['开盘价']
        df_new['low'] = df['最低价']
        df_new['high'] = df['最高价']
        df_new['close'] = df['收盘价']
        df_new['chg'] = df['涨跌额']
        df_new['pct_chg'] = df['涨跌幅']
        df_new['turn_rate'] = df['换手率']
        df_new['volume'] = df['成交量']
        df_new['turnover'] = df['成交金额']
        df_new['mkv'] = df['总市值']
        df_new['cir_mkv'] = df['流通市值']
        #df_new['tick_num'] = df['成交笔数'] #数据不完整

        if sym == '399300.SZ': # 399300.SZ缺失数据填充
            df_new['turn_rate'] = 0
            df_new['mkv'] = 0
            df_new['cir_mkv'] = 0

        df_new = df_new.iloc[::-1].reset_index(drop=True) # 按时间正序并重置index

        li_suspend = []
        li_open = [df_new['open'][0]]
        li_low = [df_new['low'][0]]
        li_high = [df_new['high'][0]]
        li_close = [df_new['close'][0]]
        li_chg = []
        li_pct_chg = []
        for r in df_new.iterrows():
            if r[1]['chg'] == 'None':
                li_suspend.append(True)
                li_open.append(li_close[-1])
                li_low.append(li_close[-1])
                li_high.append(li_close[-1])
                li_close.append(li_close[-1])
                li_chg.append(0)
                li_pct_chg.append(0)
            else:
                li_suspend.append(False)
                li_open.append(r[1]['open'])
                li_low.append(r[1]['low'])
                li_high.append(r[1]['high'])
                li_close.append(r[1]['close'])
                li_chg.append(r[1]['chg'])
                li_pct_chg.append(r[1]['pct_chg'])

        df_new['suspend'] = li_suspend
        df_new['open'] = li_open[1:]
        df_new['low'] = li_low[1:]
        df_new['high'] = li_high[1:]
        df_new['close'] = li_close[1:]
        df_new['chg'] = li_chg
        df_new['pct_chg'] = li_pct_chg

        df_new.to_csv('database/sym_data/%s.csv'%sym,encoding='gbk')
    except:
        li_failed.append(sym)
print('=====历史数据处理完成=====')
print('处理失败：',li_failed)

# 处理原始财务指标
li_all_sym = os.listdir('database/mfi_data_raw')
#li_all_sym = ['600999.SH']

li_failed = []
for fn in li_all_sym:
    sym = re.split('.csv', fn)[0]
    print('处理中：',sym)
    try:
        df = pd.read_csv('database/mfi_data_raw/%s.csv'%sym,encoding='gbk')
        dict_mfi = {}
        dict_mfi['post_date'] = list(df.T[1].index[1:])
        dict_mfi['eps'] = list(list(df.T[0])[1:]) # 每股收益
        dict_mfi['bps'] = list(list(df.T[1])[1:]) # 每股净资产
        dict_mfi['cfps'] = list(list(df.T[2])[1:]) # 每股净现金流
        dict_mfi['income'] = list(list(df.T[3])[1:]) # 主营收入
        dict_mfi['main_profit'] = list(list(df.T[4])[1:])  # 主营利润
        dict_mfi['profit'] = list(list(df.T[5])[1:])  # 营业利润
        dict_mfi['inv_profit'] = list(list(df.T[6])[1:])  # 投资收益
        dict_mfi['other_profit'] = list(list(df.T[7])[1:])  # 营业外收支
        dict_mfi['total_profit'] = list(list(df.T[8])[1:])  # 利润总额
        dict_mfi['net_profit'] = list(list(df.T[9])[1:])  # 净利润
        dict_mfi['net_profit_rec'] = list(list(df.T[10])[1:])  # 扣非净利润
        dict_mfi['cash_flow'] = list(list(df.T[11])[1:])  # 经营净现金流
        dict_mfi['cash_add'] = list(list(df.T[12])[1:])  # 现金增加额
        dict_mfi['total_asset'] = list(list(df.T[13])[1:])  # 总资产
        dict_mfi['liquid_asset'] = list(list(df.T[14])[1:])  # 流动资产
        dict_mfi['total_liability'] = list(list(df.T[15])[1:])  # 总负债
        dict_mfi['liquid_liability'] = list(list(df.T[16])[1:])  # 流动负债
        dict_mfi['equity'] = list(list(df.T[17])[1:])  # 股东权益
        dict_mfi['roc'] = list(list(df.T[18])[1:])  # 净资产收益率

        # 将dict导入新数据表df_mfi
        df_mfi = pd.DataFrame(dict_mfi)
        df_mfi = df_mfi.iloc[::-1].reset_index(drop=True).dropna()  # 按时间正序并重置index

        df_mfi.to_csv('database/mfi_data/%s.csv'%sym,encoding='gbk')
    except:
        li_failed.append(sym)
print('=====财务指标处理完成=====')
print('处理失败：',li_failed)
