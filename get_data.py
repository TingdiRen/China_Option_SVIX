import requests
import json
import pandas as pd
import time
import os

def get_option_chain_data(underlying_code="510050", page_number=1, page_size=50):
    """
    从东方财富的实时服务器获取指定标的期权链数据。

    :param underlying_code: 标的证券代码 (例如 "510050" for 50ETF).
    :param page_number: 要获取的页码.
    :param page_size: 每页的数据条数.
    :return: 包含期权数据的 pandas DataFrame, 或在失败时返回 None.
    """
    api_url = "https://push2.eastmoney.com/api/qt/clist/get"

    # 定义需要获取的字段
    fields = "f1,f2,f3,f12,f13,f14,f298,f299,f249,f300,f330,f331,f332,f333,f334,f335,f336,f301"

    if underlying_code == '159919':
        code_ = '12'
    else:
        code_ = '10'

    fs_param = f"m:{code_}+c:{underlying_code}"

    # 请求参数
    params = {
        "pn": page_number,
        "pz": page_size,
        "po": "1",  # 降序
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f301",
        "fs": fs_param,
        "fields": fields,
        "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",  # 使用发现的有效token
        "cb": f"jQuery_callback_{int(time.time() * 1000)}",
        "_": int(time.time() * 1000),
    }

    # 必要的请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Referer': 'http://quote.eastmoney.com/'
    }

    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()

        # --- 解析JSONP响应 ---
        response_text = response.text
        start_index = response_text.find('(')
        end_index = response_text.rfind(')')
        if start_index == -1 or end_index == -1:
            print("错误: 无法解析JSONP响应。响应内容:", response_text)
            return None

        json_str = response_text[start_index + 1: end_index]
        data = json.loads(json_str)

        # --- 提取并格式化数据 ---
        if data and data.get("data") and data["data"].get("diff"):
            raw_data_list = data["data"]["diff"]

            # 如果列表为空，说明没有数据了
            if not raw_data_list:
                print(f"在第 {page_number} 页没有获取到更多数据。")
                return None

            df = pd.DataFrame(raw_data_list)

            # 定义列名映射关系
            column_mapping = {
                'f12': '期权代码',
                'f14': '期权名称',
                'f2': '期权最新价',
                'f249': '隐含波动率',
                'f298': '时间价值',
                'f299': '内在价值',
                'f300': '理论价值',
                'f301': '到期日',
                'f333': '标的名称',
                'f334': 'ETF最新价',
            }

            df.rename(columns=column_mapping, inplace=True)

            # 只保留我们定义好的列，并按指定顺序排列
            ordered_columns = [col for col in column_mapping.values() if col in df.columns]
            return df[ordered_columns]
        else:
            print("API返回成功, 但未找到有效数据。响应:", data)
            return None

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        print("收到的文本内容:", json_str)
        return None


def get_strike(text):
    if text[-1] == 'A':
        return float(text[-5:-1]) / 1000
    else:
        return float(text[-4:]) / 1000


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)

    # 设置pandas显示选项
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 2000)

    max_pages = 5
    print("正在获取 50ETF (510050) 的期权数据...")
    namespace = locals()
    for i in range(1, max_pages + 1):
        namespace[f"etf_50_data_pg{i}"] = get_option_chain_data(underlying_code="510050", page_number=i, page_size=50)

    etf_50_data = pd.concat([namespace[f"etf_50_data_pg{i}"] for i in range(1, max_pages + 1)], axis=0)
    etf_50_data['到期日'] = pd.to_datetime(etf_50_data['到期日'], format='%Y%m%d').dt.date
    etf_50_data['执行价'] = etf_50_data['期权名称'].apply(lambda x: get_strike(x))
    etf_50_data.to_csv('data/etf_510050_data.csv', index=False)

    print("正在获取 300ETF (510300) 的期权数据...")
    namespace = locals()
    for i in range(1, max_pages + 1):
        namespace[f"etf_300_data_pg{i}"] = get_option_chain_data(underlying_code="510300", page_number=i, page_size=50)

    etf_300_data = pd.concat([namespace[f"etf_300_data_pg{i}"] for i in range(1, max_pages + 1)], axis=0)
    etf_300_data['到期日'] = pd.to_datetime(etf_300_data['到期日'], format='%Y%m%d').dt.date
    etf_300_data['执行价'] = etf_300_data['期权名称'].apply(lambda x: get_strike(x))
    etf_300_data.to_csv('data/etf_510300_data.csv', index=False)

    print("正在获取 300ETF2 (159919) 的期权数据...")
    namespace = locals()
    for i in range(1, max_pages + 1):
        namespace[f"etf_3002_data_pg{i}"] = get_option_chain_data(underlying_code="159919", page_number=i, page_size=50)

    etf_3002_data = pd.concat([namespace[f"etf_3002_data_pg{i}"] for i in range(1, max_pages + 1)], axis=0)
    etf_3002_data['到期日'] = pd.to_datetime(etf_3002_data['到期日'], format='%Y%m%d').dt.date
    etf_3002_data['执行价'] = etf_3002_data['期权名称'].apply(lambda x: get_strike(x))
    etf_3002_data.to_csv('data/etf_159919_data.csv', index=False)

    print("完成，数据存储在data文件夹")
