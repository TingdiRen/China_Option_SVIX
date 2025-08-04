import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. 准备工作和参数设定 ---
# df = pd.read_csv('data/etf_510050_data.csv')
# df = pd.read_csv('data/etf_510300_data.csv')
df = pd.read_csv('data/etf_159919_data.csv')

# 假设参数
CALCULATION_DATE = datetime.strptime('2025-08-04', '%Y-%m-%d')
RISK_FREE_RATE = 0.02  # 假设年化无风险利率为 2.0%

# --- 2. 数据预处理 ---

# 清理和转换数据类型
df['到期日'] = pd.to_datetime(df['到期日'])
df['执行价'] = pd.to_numeric(df['执行价'], errors='coerce')
df['期权最新价'] = pd.to_numeric(df['期权最新价'], errors='coerce')
df['ETF最新价'] = pd.to_numeric(df['ETF最新价'], errors='coerce')

# 识别期权类型（看涨/看跌）
df['类型'] = df['期权名称'].apply(lambda x: 'Call' if '购' in x else 'Put')

# 计算距离到期日的时间（以年为单位）
# 使用365天/年以考虑闰年
df['T'] = (df['到期日'] - CALCULATION_DATE).dt.days / 365

# 删除到期时间小于等于0的数据（如果存在）
df = df[df['T'] > 0].copy()


# --- 3. SVIX 计算核心函数 ---

def calculate_svix_for_expiry(expiry_df, risk_free_rate):
    """
    为单个到期日的期权系列计算SVIX指数。

    Args:
        expiry_df (pd.DataFrame): 包含单个到期日所有期权数据的DataFrame。
        risk_free_rate (float): 年化无风险利率。

    Returns:
        tuple: (svix, forward_price) 或 (None, None) 如果计算失败。
    """
    if expiry_df.empty:
        return None, None

    # 获取该到期日共有的参数
    S = expiry_df['ETF最新价'].iloc[0]
    T = expiry_df['T'].iloc[0]

    # 计算总无风险利率 (Gross Risk-Free Rate)，使用连续复利
    R_f = np.exp(risk_free_rate * T)

    # a. 确定远期价格 F (Forward Price)
    # 方法：找到看涨和看跌期权价格差异最小的执行价 K*
    # F = K* + R_f * (C - P)

    # 将数据整理为每个执行价都有看涨和看跌价格
    pivot = expiry_df.pivot_table(index='执行价', columns='类型', values='期权最新价').dropna()
    if pivot.empty:
        return None, None  # 如果没有成对的期权，无法计算F

    pivot['diff'] = abs(pivot['Call'] - pivot['Put'])
    min_diff_strike = pivot['diff'].idxmin()

    C_at_min = pivot.loc[min_diff_strike, 'Call']
    P_at_min = pivot.loc[min_diff_strike, 'Put']

    forward_price = min_diff_strike + R_f * (C_at_min - P_at_min)

    # b. 筛选价外期权 (Out-of-the-money options)
    # 看跌期权：执行价 < F
    # 看涨期权：执行价 >= F
    otm_puts = expiry_df[(expiry_df['类型'] == 'Put') & (expiry_df['执行价'] < forward_price)]
    otm_calls = expiry_df[(expiry_df['类型'] == 'Call') & (expiry_df['执行价'] >= forward_price)]

    otm_options = pd.concat([otm_puts, otm_calls]).sort_values('执行价').reset_index(drop=True)

    if len(otm_options) < 3:  # 需要至少3个点来计算ΔK
        return None, None

    # c. 计算每个行权价的间距 ΔK (delta_K)
    strikes = otm_options['执行价'].values
    delta_K = np.zeros_like(strikes)

    # 中间部分
    delta_K[1:-1] = (strikes[2:] - strikes[:-2]) / 2
    # 两个端点
    delta_K[0] = strikes[1] - strikes[0]
    delta_K[-1] = strikes[-1] - strikes[-2]

    otm_options['delta_K'] = delta_K

    # d. 计算积分近似值（离散求和）
    integral_sum = (otm_options['期权最新价'] * otm_options['delta_K']).sum()

    # e. 代入SVIX²公式
    # SVIX² = (2 / (T * R_f * S²)) * integral_sum
    # 原论文公式为 1/R_f,t * var*，其中 var* = 2/S² * integral.
    # 而SVIX² = (1/(T-t)) * var_t*(R_T)/R_f,t = (1/T) * (1/R_f) * (2/S²) * Integral
    svix_squared = (2 / (T * R_f * S ** 2)) * integral_sum

    # 开方得到SVIX，并转换为百分比形式
    svix = np.sqrt(svix_squared) * 100

    return svix, forward_price


# --- 4. 循环计算并展示结果 ---

results = {}
unique_expiry_dates = df['到期日'].unique()

print(f"--- SVIX 计算结果 ---")
print(f"基于假设：计算日 = {CALCULATION_DATE.date()}, 无风险利率 = {RISK_FREE_RATE:.2%}\n")
print(f"{'到期日':<15} {'SVIX (%)':<15} {'远期价格 (F)':<15}")
print("-" * 47)

for expiry in sorted(unique_expiry_dates):
    expiry_df = df[df['到期日'] == expiry]
    try:
        svix_val, f_val = calculate_svix_for_expiry(expiry_df, RISK_FREE_RATE)
        if svix_val is not None:
            results[expiry.date()] = {'SVIX': svix_val, 'F': f_val}
            print(f"{str(expiry.date()):<15} {svix_val:<15.2f} {f_val:<15.4f}")
        else:
            print(f"{str(expiry.date()):<15} {'计算失败':<15} {'N/A'}")
    except Exception as e:
        print(f"{str(expiry.date()):<15} 错误: {e}")

print("-" * 47)