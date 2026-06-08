"""
智能投资分析平台 · 专业版 最终稳定版
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from data_fetcher import DataFetcher
from analyzer import TechnicalAnalyzer
from predictor import PricePredictor
from recommender import InvestmentRecommender
from reporter import ReportGenerator

st.set_page_config(page_title="智能投资分析平台·专业版", page_icon="📈", layout="wide")

# Session State
if 'watchlist' not in st.session_state: st.session_state.watchlist = ['000001','600519','300750']
if 'selected_stock' not in st.session_state: st.session_state.selected_stock = '000001'
if 'pred_code' not in st.session_state: st.session_state.pred_code = ''
if 'pred_type' not in st.session_state: st.session_state.pred_type = '股票'
if 'ai_ptype' not in st.session_state: st.session_state.ai_ptype = '股票'
if 'ai_code' not in st.session_state: st.session_state.ai_code = '000001'
if 'fund_n' not in st.session_state: st.session_state.fund_n = 10
if 'portfolio_risk' not in st.session_state: st.session_state.portfolio_risk = '平衡型'
if 'portfolio_amount' not in st.session_state: st.session_state.portfolio_amount = 100000

@st.cache_resource
def init_services():
    return {
        'fetcher': DataFetcher(),
        'recommender': InvestmentRecommender(),
        'reporter': ReportGenerator(),
        'predictor': PricePredictor()
    }
services = init_services()

# 侧边栏
with st.sidebar:
    st.title("📈 智能投资分析平台")
    st.caption("专业版")
    st.markdown("---")
    page = st.radio("", ["🏠 市场概览","🔥 板块行情","💹 北向资金","🔍 基金推荐","📊 个股分析","📈 AI预测","💼 投资组合","⭐ 自选股","📋 报告中心"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("⭐ 自选股")
    new_stock = st.text_input("", placeholder="添加代码", label_visibility="collapsed")
    c1,c2 = st.columns(2)
    if c1.button("➕"): 
        if new_stock and len(new_stock)==6 and new_stock not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_stock); st.rerun()
    if c2.button("🗑️"): st.session_state.watchlist=[]; st.rerun()
    for w in st.session_state.watchlist: st.caption(w)
    st.markdown("---")
    # 自动刷新
    st.markdown("---")
    auto_refresh = st.checkbox("🔄 自动刷新（每60秒）")
    if auto_refresh:
        st.caption("数据每60秒自动更新")
        time.sleep(60)
        st.rerun()
    if st.button("🧹 清除缓存"): st.cache_data.clear(); st.rerun()

# ============ 市场概览 ============
if page == "🏠 市场概览":
    st.header("📊 市场概览")
    indices = services['fetcher'].get_market_index()
    if not indices.empty:
        cols = st.columns(4)
        for i,(_,row) in enumerate(indices.head(12).iterrows()):
            with cols[i%4]: st.metric(row['名称'], f"{row['最新价']:.2f}", f"{row['涨跌幅(%)']:+.2f}%")
        st.markdown("---")
        fig = px.bar(indices, x='名称', y='涨跌幅(%)', color='涨跌幅(%)', color_continuous_scale=['#00b894','#dfe6e9','#e94560'])
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("非交易日，请在工作日查看")

# ============ 板块行情 ============
elif page == "🔥 板块行情":
    st.header("🔥 行业板块")
    sectors = services['fetcher'].get_sector_data()
    if not sectors.empty: st.dataframe(sectors.style.background_gradient(subset=['涨跌幅(%)'], cmap='RdYlGn'), use_container_width=True)
    else: st.info("非交易日暂无数据")

# ============ 北向资金 ============
elif page == "💹 北向资金":
    st.header("💹 北向资金")
    north = services['fetcher'].get_north_flow()
    if not north.empty and len(north) > 0:
        total = north['北向净流入(亿)'].sum()
        st.metric("近30日累计净流入", f"{total:.2f}亿")
        fig = px.bar(north.tail(20), x='日期', y='北向净流入(亿)',
                    color='北向净流入(亿)', color_continuous_scale=['#00b894','white','#e94560'])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(north.tail(10), use_container_width=True)
    else:
        st.info("📌 今日暂无北向资金数据（非交易日或数据源暂不可用）")

# ============ 基金推荐 ============
# ============ 基金推荐 ============
elif page == "🔍 基金推荐":
    st.header("🔍 智能基金推荐")
    col1, col2 = st.columns([2, 1])
    with col1:
        filter_level = st.selectbox("筛选等级", ["全部", "🏆 强烈推荐", "⭐ 推荐", "👍 关注"])
    with col2:
        n = st.slider("数量", 5, 30, st.session_state.fund_n, key='fund_n')
    
    if st.button("🔄 刷新"):
        st.cache_data.clear()
        st.rerun()
    
    recs = services['recommender'].get_buy_signal_funds(n=30)
    if recs is not None and len(recs) > 0:
        # 推荐等级
        def tag(row):
            s = float(row.get('score', 0))
            m = float(row.get('month_return', 0))
            y = float(row.get('year_return', 0))
            if s > 80 and m > 5 and y > 20:
                return '🏆 强烈推荐'
            elif s > 60 and m > 2 and y > 10:
                return '⭐ 推荐'
            elif s > 40 and m > 0:
                return '👍 关注'
            return '➖ 一般'
        
        recs['推荐等级'] = recs.apply(tag, axis=1)
        if filter_level != "全部":
            recs = recs[recs['推荐等级'] == filter_level]
        recs = recs.head(n)
        
        # 构建显示表
        display = pd.DataFrame()
        col_map = {
            'code': '基金代码', 'name': '基金名称',
            '推荐等级': '推荐', 'score': '综合评分',
            'month_return': '近1月(%)', 'q3_return': '近3月(%)',
            'year_return': '近1年(%)', 'half_return': '近6月(%)',
            'y2_return': '近2年(%)', 'y3_return': '近3年(%)',
            'tech_recommendation': '技术信号',
            'predicted_direction': 'AI预测', 'confidence': '置信度'
        }
        for old, new in col_map.items():
            if old in recs.columns:
                display[new] = recs[old].values
        
        st.success(f"✅ 筛选出 {len(display)} 只基金")
        st.dataframe(display, use_container_width=True)
        
        # 一键预测
        pred_cols = st.columns(min(5, len(recs)))
        for i, (_, row) in enumerate(recs.head(5).iterrows()):
            with pred_cols[i]:
                if st.button(f"📈 {row['name'][:6]}", key=f"p_{row['code']}"):
                    st.session_state.pred_code = row['code']
                    st.session_state.pred_type = '基金'
                    st.rerun()
    else:
        st.warning("暂无数据")
# ============ 个股分析 ============
elif page == "📊 个股分析":
    st.header("📊 个股分析")
    keyword = st.text_input("输入代码或名称","000001")
    if st.button("🔍 搜索"):
        if keyword.isdigit() and len(keyword)==6: st.session_state.selected_stock=keyword
        else:
            stocks=services['fetcher'].get_all_a_stocks()
            if not stocks.empty:
                m=stocks[stocks['name'].str.contains(keyword,na=False)]
                if len(m)>0: st.session_state.selected_stock=m.iloc[0]['code']; st.success(f"{m.iloc[0]['name']}({m.iloc[0]['code']})")
    code=st.session_state.selected_stock
    if st.button("🚀 分析 "+code,type="primary"):
        df=services['fetcher'].get_stock_history(code,force_refresh=True)
        if not df.empty:
            quote=services['fetcher'].get_realtime_quote(code)
            if quote:
                st.subheader(f"{quote['name']}（{code}）")
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("最新",f"{quote['price']:.2f}",f"{quote['change_pct']:+.2f}%")
                c2.metric("开盘",f"{quote['open']:.2f}")
                c3.metric("最高",f"{quote['high']:.2f}")
                c4.metric("最低",f"{quote['low']:.2f}")
                c5.metric("量",f"{quote['volume']/10000:.0f}万")
            ta=TechnicalAnalyzer(); df=ta.full_analysis(df); signals=ta.get_signal_summary(df)
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("评分",signals.get('total_score',0))
            rec=signals.get('recommendation','')
            c2.metric("建议",f"{'🟢' if '买' in rec else '🔴' if '卖' in rec else '🟡'} {rec}")
            c3.metric("MACD",signals.get('macd',''))
            c4.metric("KDJ",signals.get('kdj',''))
            c5.metric("RSI",signals.get('rsi',''))
            fig=make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[0.7,0.3])
            fig.add_trace(go.Candlestick(x=df['date'],open=df['open'],high=df['high'],low=df['low'],close=df['close'],name='K线'),row=1,col=1)
            if 'MA20' in df.columns: fig.add_trace(go.Scatter(x=df['date'],y=df['MA20'],name='MA20',line=dict(color='orange')),row=1,col=1)
            if 'MA60' in df.columns: fig.add_trace(go.Scatter(x=df['date'],y=df['MA60'],name='MA60',line=dict(color='blue')),row=1,col=1)
            colors=['red' if c>=o else 'green' for c,o in zip(df['close'].tail(120),df['open'].tail(120))]
            fig.add_trace(go.Bar(x=df['date'].tail(120),y=df['volume'].tail(120),name='量',marker_color=colors),row=2,col=1)
            fig.update_layout(height=600)
            st.plotly_chart(fig,use_container_width=True)
            if 'MACD_DIF' in df.columns:
                fig2=go.Figure()
                fig2.add_trace(go.Scatter(x=df['date'],y=df['MACD_DIF'],name='DIF'))
                fig2.add_trace(go.Scatter(x=df['date'],y=df['MACD_DEA'],name='DEA'))
                fig2.add_trace(go.Bar(x=df['date'],y=df['MACD_HIST'],name='柱'))
                fig2.update_layout(height=300)
                st.plotly_chart(fig2,use_container_width=True)
        else: st.error("获取失败")

# ============ AI预测 ============
elif page == "📈 AI预测":
    st.header("📈 AI走势预测")
    jump_code=st.session_state.get('pred_code',''); jump_type=st.session_state.get('pred_type','股票')
    if jump_code: st.session_state.ai_ptype=jump_type; st.session_state.ai_code=jump_code; st.session_state.pred_code=''; st.session_state.pred_type='股票'
    ptype=st.selectbox("标的",["股票","基金"],index=0 if st.session_state.ai_ptype=='股票' else 1,key='ai_ptype')
    code=st.text_input("代码",value=st.session_state.ai_code,key='ai_code')
    if st.button("🔮 预测",type="primary"):
        if ptype=="基金":
            df=services['fetcher'].get_fund_history(code)
            if not df.empty:
                for c in ['open','high','low','close']: df[c]=df['nav']
                df['volume']=0
            target='nav'
            name=services['fetcher'].get_fund_name(code)
            if name and name!=code: st.subheader(f"🏷️ {name}（{code}）")
        else: df=services['fetcher'].get_stock_history(code); target='close'
        if not df.empty and len(df)>=60:
            predictor=PricePredictor(); result=predictor.predict(df,days_ahead=10)
            if result:
                c1,c2,c3,c4=st.columns(4)
                c1.metric("当前",f"{result['current_price']:.2f}")
                c2.metric("方向",result['direction'])
                c3.metric("变动",f"{result['expected_change_pct']:+.2f}%")
                c4.metric("置信",result['confidence'])
                dates=pd.bdate_range(start=df['date'].iloc[-1]+pd.Timedelta(days=1),periods=10,freq='B')
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=df['date'].tail(60),y=df[target].tail(60),name='历史'))
                fig.add_trace(go.Scatter(x=dates,y=result['predicted_prices'],name='预测',line=dict(dash='dash')))
                st.plotly_chart(fig,use_container_width=True)
                st.info("⚠️ 基于历史统计，仅供参考")
            else: st.warning("数据不足")
        else: st.error("需至少60个交易日")

# ============ 投资组合 ============
elif page == "💼 投资组合":
    st.header("💼 投资组合")
    risk=st.selectbox("风险偏好",["保守型","平衡型","进取型"],index=['保守型','平衡型','进取型'].index(st.session_state.portfolio_risk),key='portfolio_risk')
    amount=st.number_input("金额(元)",10000,10000000,st.session_state.portfolio_amount,key='portfolio_amount')
    if st.button("生成组合",type="primary"):
        m={'保守型':'conservative','平衡型':'balanced','进取型':'aggressive'}
        pf=services['recommender'].generate_portfolio(m[risk],amount)
        if len(pf)>0:
            pf=pf.rename(columns={'type':'类型','code':'代码','name':'名称','amount':'金额','year_return':'年收益%'})
            st.dataframe(pf,use_container_width=True)
            fig=px.pie(pf,values='金额',names='类型',hole=0.4)
            st.plotly_chart(fig,use_container_width=True)
        else: st.error("生成失败")

# ============ 自选股 ============
elif page == "⭐ 自选股":
    st.header("⭐ 自选股")
    if st.session_state.watchlist:
        data=[]
        for c in st.session_state.watchlist:
            q=services['fetcher'].get_realtime_quote(c)
            if q: data.append({'代码':c,'名称':q['name'],'最新':q['price'],'涨跌%':q['change_pct']})
        if data: st.dataframe(pd.DataFrame(data).style.background_gradient(subset=['涨跌%'],cmap='RdYlGn'),use_container_width=True)
    else: st.info("请在侧边栏添加自选股")

# ============ 报告中心 ============
elif page == "📋 报告中心":
    st.header("📋 报告中心")
    if st.button("📥 生成报告", type="primary"):
        market = services['recommender'].get_market_analysis()
        recs = services['recommender'].get_buy_signal_funds(n=10)
        summary = services['reporter'].generate_summary_text(market, recs)
        st.text(summary)
        
        # 修复：确保数据不为空再生成Excel
        if recs is not None and len(recs) > 0:
            try:
                fp = services['reporter'].generate_excel({'市场': market, '推荐': recs})
                with open(fp, 'rb') as f:
                    st.download_button("⬇️ 下载Excel", f, file_name="report.xlsx")
            except:
                st.warning("Excel生成失败，请稍后重试")
        else:
            st.info("暂无基金数据，无法生成Excel")

st.markdown("---")
st.caption("⚠️ 免责声明：本平台仅供学习参考，不构成投资建议。投资有风险，入市需谨慎。")