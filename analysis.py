# -*- coding: utf-8 -*-

"""
用于回测结果的绩效分析、绘图
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# 用于转换百分数
def format_percent(num):
    return format(num*100,'.3f')+'%'

# 计算年化收益率
def cal_annualized_returns(df_networth,trade_days=252):
    annualized_returns = (df_networth[-1]/df_networth[0]-1)*trade_days/len(df_networth)
    return annualized_returns

# 计算年化波动率
def cal_annualized_volatility(df_networth,trade_days=252):
    returns = (df_networth/df_networth.shift(1)-1).dropna()
    if pd.isna(np.std(returns)):
        return 0
    else:
        return np.sqrt(trade_days)*np.std(returns)

# 计算最大回撤
def cal_drawdown(df_networth):
    date = list(df_networth.index)
    accumulate_max_networth = np.maximum.accumulate(df_networth)
    drawdown = list((accumulate_max_networth-df_networth)/accumulate_max_networth)
    max_drawdown = max(drawdown)
    if max_drawdown == 0: # 若最大回撤为0，返回空日期
        return max_drawdown,None,None
    else:
        md_start_date = date[list(df_networth).index(max(df_networth[0:drawdown.index(max_drawdown)]))]
        md_end_date = date[drawdown.index(max_drawdown)]
        return max_drawdown,md_start_date,md_end_date

# 计算夏普比率（假定无风险利率为4%）
def cal_sharpe_ratio(df_networth,trade_days=252,risk_free=0.04):
    annualized_returns = (df_networth[-1]/df_networth[0]-1)*trade_days/len(df_networth)
    returns = (df_networth/df_networth.shift(1)-1).dropna()
    if np.std(returns) == 0 or pd.isna(np.std(returns)):
        return 0
    else:
        return (annualized_returns-risk_free)/(np.sqrt(trade_days)*np.std(returns))

# 计算Calmar比率
def cal_calmar_ratio(df_networth,trade_days=252):
    annualized_returns = cal_annualized_returns(df_networth,trade_days)
    max_drawdown = cal_drawdown(df_networth)[0]
    if max_drawdown == 0: # 最大回撤为0，则Calmar比率无穷大
        return 0
    else:
        return annualized_returns/max_drawdown

# 计算组合Beta
def cal_portfolio_beta(df_networth,df_networth_benchmark):
    returns = (df_networth/df_networth.shift(1)-1).dropna()
    returns_benchmark = (df_networth_benchmark/df_networth_benchmark.shift(1)-1).dropna()
    if len(returns) > 1: # 数据不足，不计算协方差
        beta = np.cov(returns,returns_benchmark)[0,1]/np.cov(returns_benchmark)
        return beta
    else:
        return 0

# 计算组合Alpha
def cal_portfolio_alpha(df_networth,df_networth_benchmark,trade_days=252,risk_free=0.04):
    annualized_returns = (df_networth[-1]/df_networth[0]-1)*trade_days/len(df_networth)
    annualized_returns_benchmark = (df_networth_benchmark[-1]/df_networth_benchmark[0]-1)*trade_days/len(df_networth_benchmark)
    beta = cal_portfolio_beta(df_networth,df_networth_benchmark)
    alpha = annualized_returns-(risk_free+beta*(annualized_returns_benchmark-risk_free))
    return alpha

# 输出风险指标
def output_performance(portfolios,benchmark):
    start_date = portfolios.start_date
    end_date = portfolios.end_date

    df_benchmark = pd.read_csv('database/sym_data/%s.csv'%benchmark,encoding="gbk").dropna()
    df_benchmark = df_benchmark[(df_benchmark['date_time']>=start_date)&(df_benchmark['date_time']<=end_date)].reset_index()

    all_holdings = pd.DataFrame(portfolios.all_holdings)

    df = pd.DataFrame()
    df['date_time'] = all_holdings['date_time']
    df['networth'] = all_holdings['mkt_value']/portfolios.initial_capital
    df['networth_benchmark'] = df_benchmark['close']/df_benchmark['close'][0]
    df.index = df['date_time']

    print("==========风险指标==========")
    print("年化收益率：",format_percent(cal_annualized_returns(df['networth'])))
    print("基准收益率：",format_percent(cal_annualized_returns(df['networth_benchmark'])))
    print("年化波动率：",format_percent(cal_annualized_volatility(df['networth'])))
    print('最大回撤：',format_percent(cal_drawdown(df['networth'])[0]))
    print('最大回撤起始：',cal_drawdown(df['networth'])[1])
    print('最大回撤结束：',cal_drawdown(df['networth'])[2])
    print("夏普比率：",format(cal_sharpe_ratio(df['networth']),'.3f'))
    print("Calmar比率：",format(cal_calmar_ratio(df['networth']),'.3f'))
    print("组合Beta：",format(cal_portfolio_beta(df['networth'],df['networth_benchmark']),'.3f'))
    print("组合Alpha:",format(cal_portfolio_alpha(df['networth'],df['networth_benchmark']),'.3f'))

# 绘制净值曲线
def draw_plot(portfolios,benchmark):
    start_date = portfolios.start_date
    end_date = portfolios.end_date

    df_benchmark = pd.read_csv('database/sym_data/%s.csv'%benchmark,encoding="gbk").dropna()
    df_benchmark = df_benchmark[(df_benchmark['date_time']>=start_date)&(df_benchmark['date_time']<=end_date)].reset_index()

    all_holdings = pd.DataFrame(portfolios.all_holdings)

    df = pd.DataFrame()
    df['date_time'] = all_holdings['date_time']
    df['networth'] = all_holdings['mkt_value']/portfolios.initial_capital
    df['networth_benchmark'] = df_benchmark['close']/df_benchmark['close'][0]

    fig1 = plt.figure(figsize=(12,6))
    fig1.patch.set_facecolor('white')
    ax1 = fig1.add_subplot(111,ylabel='Networth')
    ax1.set_title("Portfolio Equity Curve")
    ax1.plot(df['date_time'],df['networth'],color='red',lw=1)
    ax1.plot(df['date_time'],df['networth_benchmark'],color='blue',linestyle='--',lw=0.5)
    # 设置X轴标签密度
    trade_days = len(all_holdings['date_time'])
    ax1.xaxis.set_major_locator(ticker.MultipleLocator(int(trade_days/10)+1))

    # 标注最大回撤区间
    if cal_drawdown(df['networth'])[0] != 0:
        md_start = cal_drawdown(df['networth'])[1]
        md_end = cal_drawdown(df['networth'])[2]
        ax1.plot(df['date_time'][md_start:md_end+1],df['networth'][md_start:md_end+1],color='green',lw=1)

    plt.legend(('Equity','Benchmark','Max drawdown')) # 添加图例
    plt.xticks(rotation=15) # x轴旋转15度
    plt.grid(True) #显示网格
    plt.savefig('logs/equity_curve.png')  # 回测曲线保存到本地
    #plt.show()

