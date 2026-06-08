"""
预测模块 - LSTM深度学习 + 回归预测 + 趋势判断
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    HAS_TF = True
except:
    HAS_TF = False


class PricePredictor:
    """价格预测器"""
    
    def __init__(self):
        self.scaler = MinMaxScaler()
        self.lstm_model = None
        self.rf_model = None
        self.gb_model = None
        self.is_trained = False
    
    def prepare_data(self, df, lookback=60, target_col='close'):
        """准备训练数据"""
        if len(df) < lookback + 10:
            return None, None
        
        data = df[[target_col]].values
        scaled_data = self.scaler.fit_transform(data)
        
        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i-lookback:i, 0])
            y.append(scaled_data[i, 0])
        
        return np.array(X), np.array(y)
    
    def train_lstm(self, X, y, epochs=50, batch_size=32):
        """训练LSTM模型"""
        if not HAS_TF or X is None or len(X) < 10:
            return False
        
        try:
            X = X.reshape((X.shape[0], X.shape[1], 1))
            
            split = int(len(X) * 0.8)
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])
            
            model.compile(optimizer=Adam(0.001), loss='mse')
            model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, 
                     validation_data=(X_test, y_test), verbose=0)
            
            self.lstm_model = model
            self.is_trained = True
            return True
        except Exception as e:
            print(f"LSTM训练失败: {e}")
            return False
    
    def train_ensemble(self, X, y):
        """训练集成模型"""
        if X is None or len(X) < 10:
            return False
        
        try:
            split = int(len(X) * 0.8)
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.rf_model.fit(X_train, y_train)
            
            self.gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
            self.gb_model.fit(X_train, y_train)
            
            self.is_trained = True
            return True
        except Exception as e:
            print(f"集成模型训练失败: {e}")
            return False
    
    def predict(self, df, lookback=60, days_ahead=5):
        """预测未来价格"""
        if len(df) < lookback:
            return None
        
        target_col = 'close' if 'close' in df.columns else 'nav'
        if target_col not in df.columns:
            return None
        
        X, y = self.prepare_data(df, lookback, target_col)
        if X is None:
            return None
        
        # 训练模型
        self.train_lstm(X, y)
        self.train_ensemble(X, y)
        
        # 准备预测输入
        data = df[[target_col]].values
        scaled = self.scaler.transform(data)
        last_sequence = scaled[-lookback:]
        
        predictions = []
        
        # LSTM预测
        if self.lstm_model is not None:
            lstm_preds = []
            current_seq = last_sequence.copy()
            for _ in range(days_ahead):
                X_pred = current_seq.reshape(1, lookback, 1)
                pred = self.lstm_model.predict(X_pred, verbose=0)[0, 0]
                lstm_preds.append(pred)
                current_seq = np.roll(current_seq, -1)
                current_seq[-1] = pred
            lstm_preds = self.scaler.inverse_transform(np.array(lstm_preds).reshape(-1, 1)).flatten()
            predictions.append(('LSTM', lstm_preds))
        
        # 随机森林预测
        if self.rf_model is not None:
            X_pred = last_sequence.reshape(1, -1)
            rf_pred = self.rf_model.predict(X_pred)[0]
            rf_pred = self.scaler.inverse_transform([[rf_pred]])[0, 0]
            predictions.append(('RandomForest', [rf_pred] * days_ahead))
        
        # GBM预测
        if self.gb_model is not None:
            X_pred = last_sequence.reshape(1, -1)
            gb_pred = self.gb_model.predict(X_pred)[0]
            gb_pred = self.scaler.inverse_transform([[gb_pred]])[0, 0]
            predictions.append(('GBM', [gb_pred] * days_ahead))
        
        # 加权平均
        if predictions:
            all_preds = np.array([np.array(p[1]).flatten() for p in predictions])
            ensemble_pred = np.mean(all_preds, axis=0)
            
            current_price = df[target_col].iloc[-1]
            expected_change = (ensemble_pred[-1] - current_price) / current_price * 100
            
            return {
                'current_price': current_price,
                'predicted_prices': ensemble_pred.tolist(),
                'expected_change_pct': round(expected_change, 2),
                'direction': '上涨' if expected_change > 0 else '下跌',
                'confidence': '高' if abs(expected_change) > 5 else '中' if abs(expected_change) > 2 else '低',
              'individual_preds': []
            }
        
        return None
    
    def detect_reversal(self, df, lookback=60):
        """检测趋势反转信号"""
        if len(df) < lookback:
            return None
        
        target_col = 'close' if 'close' in df.columns else 'nav'
        if target_col not in df.columns:
            return None
        
        prices = df[target_col].values
        
        # 计算近期趋势
        recent_change = (prices[-1] - prices[-20]) / prices[-20] * 100 if len(prices) >= 20 else 0
        mid_change = (prices[-20] - prices[-40]) / prices[-40] * 100 if len(prices) >= 40 else 0
        
        # 计算波动率变化
        recent_vol = pd.Series(prices[-20:]).pct_change().std()
        mid_vol = pd.Series(prices[-40:-20]).pct_change().std() if len(prices) >= 40 else recent_vol
        
        # 判断反转信号
        signals = []
        
        # 顶部反转信号
        if recent_change < -3 and mid_change > 5:
            signals.append('顶部反转')
        
        # 底部反转信号
        if recent_change > 3 and mid_change < -5:
            signals.append('底部反转')
        
        # 波动率突变
        if recent_vol > mid_vol * 2:
            signals.append('波动加剧-可能变盘')
        
        return {
            'recent_trend': f"{recent_change:.2f}%",
            'signals': signals if signals else ['无明显反转信号'],
            'risk_level': '高' if len(signals) > 1 else '中' if signals else '低'
        }