"""
数据获取模块 - 腾讯股票 + 天天基金 + 指数板块 + 北向资金（修复版）
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import re
import json
import random

last_req = 0
MIN_GAP = 2


class DataFetcher:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}

    def _wait(self):
        global last_req
        now = time.time()
        gap = now - last_req
        if gap < MIN_GAP:
            time.sleep(MIN_GAP - gap + random.uniform(0.5, 2))
        last_req = time.time()

    def _cache_get(self, key, max_age):
        if key in self.cache and time.time() - self.cache_time.get(key, 0) < max_age:
            return self.cache[key]
        return None

    def _cache_set(self, key, data):
        self.cache[key] = data
        self.cache_time[key] = time.time()

    def get_stock_history(self, code, period='daily', days=365, force_refresh=False):
        key = f'hist_{code}_{days}'
        if not force_refresh:
            cached = self._cache_get(key, 1800)
            if cached is not None:
                return cached
        try:
            self._wait()
            symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{days},qfq"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            klines = data['data'][symbol].get('qfqday') or data['data'][symbol].get('day')
            if not klines:
                return pd.DataFrame()
            rows = [{'date': k[0], 'open': float(k[1]), 'close': float(k[2]),
                     'high': float(k[3]), 'low': float(k[4]), 'volume': float(k[5])} for k in klines]
            df = pd.DataFrame(rows)
            df['date'] = pd.to_datetime(df['date'])
            self._cache_set(key, df)
            return df
        except:
            return pd.DataFrame()

    def get_realtime_quote(self, code):
        try:
            self._wait()
            symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
            url = f"http://qt.gtimg.cn/q={symbol}"
            resp = requests.get(url, timeout=10)
            resp.encoding = 'gbk'
            fields = resp.text.split('~')
            return {
                'name': fields[1], 'code': fields[2],
                'price': float(fields[3] or 0), 'open': float(fields[5] or 0),
                'high': float(fields[33] or 0), 'low': float(fields[34] or 0),
                'preclose': float(fields[4] or 0), 'change': float(fields[31] or 0),
                'change_pct': float(fields[32] or 0), 'volume': int(fields[6] or 0), 'time': fields[30]
            }
        except:
            return None

    def get_fund_name(self, code):
        """查询基金名称"""
        try:
            self._wait()
            url = f"http://fund.eastmoney.com/{code}.html"
            resp = requests.get(url, timeout=10)
            resp.encoding = 'utf-8'
            match = re.search(r'<title>(.*?)</title>', resp.text)
            if match:
                title = match.group(1)
                name = title.split('(')[0].strip()
                return name
        except:
            pass
        return code

    def get_fund_list(self, fund_type='all'):
        key = f'fund_{fund_type}'
        cached = self._cache_get(key, 3600)
        if cached is not None:
            return cached
        try:
            self._wait()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://fund.eastmoney.com/'
            }
            type_map = {'all': 'all', 'stock': 'gp', 'mix': 'hh', 'bond': 'zq', 'index': 'zs'}
            ft = type_map.get(fund_type, 'all')
            url = f"http://fund.eastmoney.com/data/rankhandler.aspx?op=ph&dt=kf&ft={ft}&rs=&gs=0&sc=zzf&st=desc&pi=1&pn=30"
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            match = re.search(r'\[.*\]', text)
            if match:
                items = json.loads(match.group())
                rows = []
                for item in items:
                    f = item.split(',')
                    if len(f) >= 14:
                        rows.append({
                            'code': f[0], 'name': f[1],
                            'daily_return': float(f[6] or 0),
                            'week_return': float(f[7] or 0),
                            'month_return': float(f[8] or 0),
                            'q3_return': float(f[9] or 0),
                            'half_return': float(f[10] or 0),
                            'year_return': float(f[11] or 0),
                            'y2_return': float(f[12] or 0),
                            'y3_return': float(f[13] or 0)
                        })
                df = pd.DataFrame(rows)
                print(f"[天天基金] 列表成功，共{len(df)}只")
                self._cache_set(key, df)
                return df
        except Exception as e:
            print(f"[天天基金] 失败：{e}")
        return pd.DataFrame(columns=['code','name','daily_return','week_return','month_return','q3_return','half_return','year_return'])

    def get_fund_history(self, fund_code, days=365):
        key = f'fund_hist_{fund_code}_{days}'
        cached = self._cache_get(key, 3600)
        if cached is not None:
            return cached
        try:
            self._wait()
            all_rows = []
            for page in range(1, 6):
                url = f"http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={fund_code}&page={page}&per=20"
                headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://fund.eastmoney.com/'}
                resp = requests.get(url, headers=headers, timeout=10)
                match = re.search(r'<table.*?</table>', resp.text, re.S)
                if match:
                    df = pd.read_html(match.group())[0]
                    df = df.rename(columns={'净值日期': 'date', '单位净值': 'nav'})
                    all_rows.append(df)
                else:
                    break
            if all_rows:
                df = pd.concat(all_rows, ignore_index=True)
                df['date'] = pd.to_datetime(df['date'])
                df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                df = df.dropna(subset=['nav'])
                df = df.sort_values('date')
                print(f"[天天基金] {fund_code} 净值成功，共{len(df)}条")
                self._cache_set(key, df)
                return df
        except Exception as e:
            print(f"[天天基金] {fund_code} 净值失败：{e}")
        return pd.DataFrame(columns=['date', 'nav'])

    # --- 大盘指数行情 ---
    def get_market_index(self):
        key = 'market_index'
        cached = self._cache_get(key, 60)
        if cached is not None:
            return cached
        try:
            self._wait()
            codes = 'sh000001,sz399001,sz399006,sh000688,sh000300,sh000905'
            url = f"http://qt.gtimg.cn/q={codes}"
            resp = requests.get(url, timeout=10)
            resp.encoding = 'gbk'
            results = []
            for line in resp.text.strip().split('\n'):
                fields = line.split('~')
                if len(fields) > 30:
                    results.append({
                        '名称': fields[1], '最新价': float(fields[3] or 0),
                        '涨跌幅(%)': float(fields[32] or 0), '涨跌额': float(fields[31] or 0),
                        '最高': float(fields[33] or 0), '最低': float(fields[34] or 0),
                        '成交量(手)': int(fields[6] or 0)
                    })
            df = pd.DataFrame(results)
            self._cache_set(key, df)
            return df
        except:
            return pd.DataFrame()

    # --- 热门板块 ---
    def get_sector_data(self):
        key = 'sector_data'
        cached = self._cache_get(key, 300)
        if cached is not None:
            return cached
        try:
            self._wait()
            url = "http://qt.gtimg.cn/q=pt01801011,pt01801021,pt01801031,pt01801041,pt01801051,pt01801061,pt01801071,pt01801081,pt01801091,pt01801101"
            resp = requests.get(url, timeout=10)
            resp.encoding = 'gbk'
            rows = []
            for line in resp.text.strip().split('\n'):
                fields = line.split('~')
                if len(fields) > 30:
                    rows.append({
                        '板块名称': fields[1], '最新价': float(fields[3] or 0),
                        '涨跌幅(%)': float(fields[32] or 0), '领涨股': fields[2]
                    })
            df = pd.DataFrame(rows)
            if len(df) > 0:
                df = df.sort_values('涨跌幅(%)', ascending=False)
            self._cache_set(key, df)
            return df
        except:
            return pd.DataFrame()

    # --- 北向资金（修复版）---
    def get_north_flow(self):
        key = 'north_flow'
        cached = self._cache_get(key, 300)
        if cached is not None:
            return cached
        try:
            self._wait()
            # 东方财富北向资金新接口
            url = "https://push2his.eastmoney.com/api/qt/kamt.kline/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54&klt=101&lmt=30&secid=1.000001"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data and data.get('data') and data['data'].get('klines'):
                rows = []
                for item in data['data']['klines']:
                    parts = item.split(',')
                    if len(parts) >= 4:
                        net_inflow = float(parts[1]) / 10000 if parts[1] != '-' else 0
                        rows.append({
                            '日期': parts[0],
                            '北向净流入(亿)': round(net_inflow, 2)
                        })
                df = pd.DataFrame(rows)
                print(f"[北向资金] 成功，共{len(df)}条")
                self._cache_set(key, df)
                return df
        except Exception as e:
            print(f"[北向资金] 失败：{e}")
        return pd.DataFrame()

    def get_all_a_stocks(self):
        return pd.DataFrame(columns=['code','name','price','change_pct','volume','amount','turnover','pe'])

    def get_etf_list(self):
        return pd.DataFrame()