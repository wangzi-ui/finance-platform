"""
推荐引擎模块 - 简化版
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from analyzer import TechnicalAnalyzer, FundamentalAnalyzer, FundAnalyzer
from predictor import PricePredictor
import warnings
warnings.filterwarnings('ignore')


class InvestmentRecommender:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.ta = TechnicalAnalyzer()
        self.fa = FundamentalAnalyzer()
        self.fund_analyzer = FundAnalyzer()
        self.predictor = PricePredictor()

    def get_top_funds(self, n=10):
        print("正在获取基金数据...")
        stock_funds = self.fetcher.get_fund_list('stock')
        mix_funds = self.fetcher.get_fund_list('mix')
        index_funds = self.fetcher.get_fund_list('index')
        all_funds = pd.concat([stock_funds, mix_funds, index_funds], ignore_index=True)
        all_funds = all_funds.drop_duplicates(subset=['code'])
        ranked = self.fund_analyzer.rank_funds(all_funds, top_n=n * 3)
        return ranked.head(n)

    def get_buy_signal_funds(self, n=5):
        funds = self.get_top_funds(n * 2)
        if funds is None or len(funds) == 0:
            return pd.DataFrame()
        result = funds.head(n).copy()
        result['score'] = result['year_return'].astype(float)
        result = result.sort_values('score', ascending=False)
        return result

    def get_market_analysis(self):
        return {
            'market_status': '震荡整理',
            'strategy': '控制仓位，逢低分批布局',
            'up_ratio': 50.0,
            'avg_change': 0.0,
            'indices': [],
            'sector_leaders': []
        }

    def generate_portfolio(self, risk_level='balanced', amount=100000):
        allocation = {'债券型': 0.3, '混合型': 0.3, '股票型': 0.3, '货币型': 0.1}
        portfolio = []
        for fund_type, ratio in allocation.items():
            if ratio == 0:
                continue
            alloc_amount = amount * ratio
            funds = self.fetcher.get_fund_list('stock')
            if not funds.empty and len(funds) >= 3:
                top3 = funds.head(3)
                for _, fund in top3.iterrows():
                    portfolio.append({
                        'type': fund_type,
                        'code': fund['code'],
                        'name': fund['name'],
                        'amount': round(alloc_amount / 3, 2),
                        'year_return': fund.get('year_return', 0),
                        'score': 0
                    })
        return pd.DataFrame(portfolio)