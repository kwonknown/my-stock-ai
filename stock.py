import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. 초고속 데이터 엔진 (프리마켓 보정)
@st.cache_data(ttl=30) # 30초 단위 갱신으로 실시간성 강화
def get_realtime_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # 미국장 프리마켓 가격 포함 시도
        info = stock.info
        current_price = info.get('ask') or info.get('regularMarketPrice') or info.get('previousClose')
        
        df = stock.history(period="1y")
        if not df.empty and current_price:
            df.iloc[-1, df.columns.get_loc('Close')] = current_price # 현재가 강제 보정
        return df, info
    except: return None, None

# 2. 보조지표 및 실전 승률
def analyze_master(df, info):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    curr = df.iloc[-1]
    cp, vwap, roe = float(curr['Close']), float(curr['VWAP']), info.get('returnOnEquity', 0) * 100
    
    # [급등주 대응] 이격도가 너무 크면 승률 하향 조정
    score = 75
    if cp > vwap: score += 15
    if cp > vwap * 1.3: score -= 20 # 과열 경보
    return df, min(score, 100)

# --- 메인 화면 ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")
ticker_input = st.sidebar.text_input("종목 입력", value="KELYB") # 켈리 서비스 바로 확인

if st.sidebar.button("🔄 실시간 동기화"):
    st.cache_data.clear()
    st.rerun()

data_raw, info = get_realtime_data(ticker_input)

if data_raw is not None:
    data, sc = analyze_master(data_raw, info)
    cp = data.iloc[-1]['Close']
    vwap = data.iloc[-1]['VWAP']
    
    st.header(f"{info.get('longName', ticker_input)} ({ticker_input})")
    c1, c2, c3 = st.columns(3)
    c1.metric("🔥 실시간 보정가", f"${cp:,.2f}")
    c2.metric("🟢 스마트 승률", f"{sc}%")
    c3.metric("🎯 세력 평단", f"${vwap:,.2f}")

    fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
    fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📝 상세 진단")
    st.write(f"현재가는 세력 평단 대비 **{((cp/vwap)-1)*100:.1f}%** 위치에 있습니다.")
    if cp > vwap * 1.2: st.warning("⚠️ **단기 과열:** 수익권이라면 일부 익절을 고려하세요!")
