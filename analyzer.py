"""
分析模块 - 技术分析 + 基本面评估 + 基金多维评估
"""
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class TechnicalAnalyzer:
    """技术分析类"""
    
    @staticmethod
    def calc_ma(df, periods=[5, 10, 20, 60, 120, 250]):
        """计算移动平均线"""
        for p in periods:
            if 'close' in df.columns and len(df) >= p:
                df[f'MA{p}'] = df['close'].rolling(window=p).mean()
        return df
    
    @staticmethod
    def calc_macd(df, fast=12, slow=26, signal=9):
        """计算MACD"""
        if 'close' not in df.columns or len(df) < slow:
            return df
        df['EMA_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df['EMA_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df['MACD_DIF'] = df['EMA_fast'] - df['EMA_slow']
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=signal, adjust=False).mean()
        df['MACD_HIST'] = 2 * (df['MACD_DIF'] - df['MACD_DEA'])
        return df
    
    @staticmethod
    def calc_kdj(df, n=9, m1=3, m2=3):
        """计算KDJ"""
        if 'close' not in df.columns or len(df) < n:
            return df
        low_list = df['low'].rolling(window=n).min()
        high_list = df['high'].rolling(window=n).max()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        df['KDJ_K'] = rsv.ewm(com=m1-1).mean()
        df['KDJ_D'] = df['KDJ_K'].ewm(com=m2-1).mean()
        df['KDJ_J'] = 3 * df['KDJ_K'] - 2 * df['KDJ_D']
        return df
    
    @staticmethod
    def calc_rsi(df, periods=[6, 12, 24]):
        """计算RSI"""
        for p in periods:
            if 'close' not in df.columns or len(df) < p:
                continue
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=p).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=p).mean()
            rs = gain / loss
            df[f'RSI{p}'] = 100 - (100 / (1 + rs))
        return df
    
    @staticmethod
    def calc_bollinger(df, period=20, std=2):
        """计算布林带"""
        if 'close' not in df.columns or len(df) < period:
            return df
        df['BOLL_MID'] = df['close'].rolling(window=period).mean()
        std_dev = df['close'].rolling(window=period).std()
        df['BOLL_UP'] = df['BOLL_MID'] + std * std_dev
        df['BOLL_DN'] = df['BOLL_MID'] - std * std_dev
        df['BOLL_WIDTH'] = (df['BOLL_UP'] - df['BOLL_DN']) / df['BOLL_MID'] * 100
        return df
    
    @staticmethod
    def calc_atr(df, period=14):
        """计算ATR（平均真实波幅）"""
        if len(df) < period:
            return df
        high, low, close = df['high'], df['low'], df['close']
        df['TR'] = np.maximum(
            high - low,
            np.maximum(abs(high - close.shift()), abs(low - close.shift()))
        )
        df['ATR'] = df['TR'].rolling(window=period).mean()
        return df
    
    @staticmethod
    def calc_obv(df):
        """计算OBV能量潮"""
        if 'close' not in df.columns or 'volume' not in df.columns:
            return df
        df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        return df
    
    def full_analysis(self, df):
        """全面技术分析"""
        df = self.calc_ma(df)
        df = self.calc_macd(df)
        df = self.calc_kdj(df)
        df = self.calc_rsi(df)
        df = self.calc_bollinger(df)
        df = self.calc_atr(df)
        df = self.calc_obv(df)
        return df
    
    def get_signal_summary(self, df):
        """生成技术信号汇总"""
        if len(df) < 60:
            return {}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        signals = {}
        
        # 均线信号
        if 'close' in df.columns and 'MA20' in df.columns:
            signals['ma_trend'] = '多头' if latest['close'] > latest['MA20'] else '空头'
            if 'MA5' in df.columns and 'MA20' in df.columns:
                signals['ma_cross'] = '金叉' if latest['MA5'] > latest['MA20'] and prev.get('MA5', 0) <= prev.get('MA20', 0) else '死叉' if latest['MA5'] < latest['MA20'] else '维持'
        
        # MACD信号
        if 'MACD_DIF' in df.columns and 'MACD_DEA' in df.columns:
            signals['macd'] = '多头' if latest['MACD_DIF'] > latest['MACD_DEA'] else '空头'
            if 'MACD_HIST' in df.columns:
                signals['macd_momentum'] = '增强' if latest['MACD_HIST'] > prev.get('MACD_HIST', 0) else '减弱'
        
        # KDJ信号
        if 'KDJ_J' in df.columns:
            j_val = latest['KDJ_J']
            if j_val > 100:
                signals['kdj'] = '超买'
            elif j_val < 0:
                signals['kdj'] = '超卖'
            elif j_val > 80:
                signals['kdj'] = '偏强'
            elif j_val < 20:
                signals['kdj'] = '偏弱'
            else:
                signals['kdj'] = '中性'
        
        # RSI信号
        if 'RSI6' in df.columns:
            rsi = latest['RSI6']
            if rsi > 80:
                signals['rsi'] = '超买'
            elif rsi < 20:
                signals['rsi'] = '超卖'
            else:
                signals['rsi'] = '正常'
        
        # 布林带位置
        if 'BOLL_UP' in df.columns:
            close = latest['close']
            if close > latest['BOLL_UP']:
                signals['boll'] = '突破上轨'
            elif close < latest['BOLL_DN']:
                signals['boll'] = '跌破下轨'
            elif close > latest['BOLL_MID']:
                signals['boll'] = '中轨上方'
            else:
                signals['boll'] = '中轨下方'
        
        # 综合评分
        score = 0
        score += 1 if signals.get('ma_trend') == '多头' else -1
        score += 1 if signals.get('macd') == '多头' else -1
        score += 1 if signals.get('kdj') in ['超卖', '偏弱'] else -1 if signals.get('kdj') in ['超买'] else 0
        score += 1 if signals.get('rsi') == '超卖' else -1 if signals.get('rsi') == '超买' else 0
        score += 1 if signals.get('boll') in ['跌破下轨', '中轨下方'] else -1 if signals.get('boll') == '突破上轨' else 0
        
        signals['total_score'] = score
        signals['recommendation'] = '强烈买入' if score >= 4 else '买入' if score >= 2 else '观望' if score >= -1 else '卖出' if score >= -3 else '强烈卖出'
        
        return signals


class FundamentalAnalyzer:
    """基本面分析类"""
    
    @staticmethod
    def calc_sharpe_ratio(returns, risk_free_rate=0.03):
        """计算夏普比率"""
        if len(returns) < 2:
            return 0
        excess_returns = returns - risk_free_rate / 252
        if excess_returns.std() == 0:
            return 0
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
    
    @staticmethod
    def calc_max_drawdown(nav_series):
        """计算最大回撤"""
        if len(nav_series) < 2:
            return 0
        cumulative = (1 + nav_series).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    @staticmethod
    def calc_sortino_ratio(returns, risk_free_rate=0.03):
        """计算索提诺比率"""
        if len(returns) < 2:
            return 0
        downside = returns[returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return 0
        excess = returns.mean() - risk_free_rate / 252
        return np.sqrt(252) * excess / downside.std()
    
    @staticmethod
    def calc_win_rate(returns):
        """计算胜率"""
        if len(returns) == 0:
            return 0
        return (returns > 0).sum() / len(returns)
    
    @staticmethod
    def calc_calmar_ratio(returns):
        """计算卡玛比率"""
        if len(returns) < 2:
            return 0
        annual_return = returns.mean() * 252
        max_dd = abs(FundamentalAnalyzer.calc_max_drawdown(returns))
        return annual_return / max_dd if max_dd != 0 else 0


class FundAnalyzer:
    """基金分析类"""
    
    def __init__(self):
        self.ta = TechnicalAnalyzer()
        self.fa = FundamentalAnalyzer()
    
    def score_fund(self, fund_row):
        """对单只基金打分"""
        score = 0
        
        # 收益率评分（近1月、3月、6月、1年）
        periods = {
            'month_return': 20, 'q3_return': 20,
            'half_return': 20, 'year_return': 40
        }
        for col, weight in periods.items():
            val = float(fund_row.get(col, 0) or 0)
            if val > 20: score += weight
            elif val > 10: score += weight * 0.8
            elif val > 5: score += weight * 0.6
            elif val > 0: score += weight * 0.3
            elif val > -5: score += weight * 0.1
        
        # 稳定性加分
        vals = [float(fund_row.get(c, 0) or 0) for c in periods.keys()]
        if all(v > 0 for v in vals):
            score += 10
        if all(v > 5 for v in vals):
            score += 10
        
        return score
    
    def rank_funds(self, fund_df, top_n=20):
        """基金排名"""
        if fund_df.empty:
            return pd.DataFrame()
        
        df = fund_df.copy()
        df['score'] = df.apply(self.score_fund, axis=1)
        df = df.sort_values('score', ascending=False)
        return df.head(top_n)