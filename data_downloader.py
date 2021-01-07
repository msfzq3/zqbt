# -*- coding: utf-8 -*-

"""
通过网易财经爬取股票数据
实时行情API：http://api.money.126.net/data/feed/0600000
历史数据：http://quotes.money.163.com/service/chddata.html?code=0600000
财务指标：http://quotes.money.163.com/service/zycwzb_600000.html
"""

import tushare as ts
import requests
import time
import os

# PART1. 获取股票代码列表

#sym_list = list(ts.get_stock_basics().index) # 全部A股
#sym_list = list(ts.get_zz500s()['code']) # 中证500
sym_list = list(ts.get_hs300s()['code']) # 沪深300
#print(sym_list)

sym_pool = []
for sym in sym_list:
    if sym.startswith('6'):
        ss = sym+'.SH'
    else:
        ss = sym+'.SZ'
    sym_pool.append(ss)
print('股票数量：',len(sym_pool))

# PART2. 历史数据下载

sym_pool.append('399300.SZ') # 添加沪深300指数
for i,sym in enumerate(sym_pool):
    if sym.endswith('.SZ'):
        ss = '1'+sym[:6]
    else:
        ss = '0'+sym[:6]
    url='http://quotes.money.163.com/service/chddata.html?code='+ss
    file_name = 'database/sym_data_raw/%s.csv'%sym
    while True:
        try:
            r = requests.get(url)
            if r.status_code != 200:
                print('连接失败：', sym)
                time.sleep(1) # 连接失败则暂停1秒
                continue
            else:
                with open(file_name,"wb") as f:
                    f.write(r.content)
                print('下载中：', sym)
                time.sleep(0.01) # 间隔0.01秒
                break
        except:
            print('下载异常：',sym)
            break
print('=====历史数据下载完成=====')

# PART3. 财务指标下载

for i,sym in enumerate(sym_pool):
    ss = sym[:6]
    url='http://quotes.money.163.com/service/zycwzb_'+ss+'.html'
    file_name = 'database/mfi_data_raw/%s.csv'%sym
    while True:
        try:
            r = requests.get(url)
            if r.status_code != 200:
                print('连接失败：', sym)
                time.sleep(1) # 连接失败则暂停1秒
                continue
            else:
                with open(file_name,"wb") as f:
                    f.write(r.content)
                print('下载中：', sym)
                time.sleep(0.01) # 间隔0.01秒
                break
        except:
            print('下载异常：',sym)
            break
print('=====财务指标下载完成=====')