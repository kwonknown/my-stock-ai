import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. 앱 설정 및 세션 상태 (종목 이동용)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

if 'selected_stock' not in st.session_state:
    st.session_state['selected_stock'] = "삼성전자"

@st.cache_data(ttl=300) # 5분간 데이터 유지하여 한도 보호
def get_stock_data_final(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if df.empty: return None, None
        return df, stock.info
    except: return None, None

# 2. 통합 지표 및 승률 계산
def analyze_stock(df, info):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    curr = df.iloc[-1]
    cp, vwap, ma = float(curr['Close']), float(curr['VWAP']), float(curr['MA20'])
    rsi, roe = float(curr['RSI']), info.get('returnOnEquity', 0) * 100
    
    # 엄격한 보수적 필터
    if cp < vwap and cp < ma: score = 40
    else:
        score = 70
        if cp > vwap: score += 10
        if cp > ma: score += 10
        if 40 < rsi < 65: score += 10
    return df, min(score, 100)

# --- 사이드바: 종목 발굴 엔진 복구 ---
st.sidebar.header("📡 글로벌 마켓 엔진")
input_q = st.sidebar.text_input("종목명 직접 입력", value=st.session_state['selected_stock'])

if st.sidebar.button("🔄 데이터 강제 갱신"):
    st.cache_data.clear()
    st.rerun()

# [복구된 추천 엔진]
sectors = {
    "AI/반도체": ["NVDA", "AMD", "005930.KS", "000660.KS"],
    "빅테크": ["AAPL", "MSFT", "PLTR", "TSLA"],
    "우량주": ["214450.KQ", "000720.KS", "035420.KS"]
}

st.sidebar.write("---")
st.sidebar.subheader("💎 실시간 우량주 추천")
if st.sidebar.button("🚀 전 섹터 전수 조사 시작"):
    with st.sidebar:
        for sec, tks in sectors.items():
            st.markdown(f"**[{sec}]**")
            for t in tks:
                try:
                    d_raw, s_info = get_stock_data_final(t)
                    if d_raw is not None:
                        _, sc = analyze_stock(d_raw, s_info)
                        if sc >= 75: # 75% 이상만 노출
                            if st.button(f"✅ {t} ({sc}%)", key=f"rec_{t}"):
                                st.session_state['selected_stock'] = t
                                st.rerun()
                except: continue

# --- 메인 대시보드 ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")

if input_q != st.session_state['selected_stock']:
    st.session_state['selected_stock'] = input_q

ticker = st.session_state['selected_stock']
data_raw, info = get_stock_data_final(ticker)

if data_raw is not None:
    data, sc = analyze_stock(data_raw, info)
    curr = data.iloc[-1]
    cp, vwap, roe = float(curr['Close']), float(curr['VWAP']), info.get('returnOnEquity', 0) * 100
    
    st.header(f"{info.get('longName', ticker)} ({ticker})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📈 현재가", f"{cp:,.2f}")
    c2.metric("🟢 스마트 승률", f"{sc}%")
    c3.metric("🎯 세력 평단", f"{vwap:,.2f}")
    c4.metric("📊 ROE", f"{roe:.1f}%")

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='주가')])
        fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
        fig.update_layout(height=550, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("🔍 상세 지표 분석")
        st.write(f"{'✅' if cp > vwap else '❌'} **수급:** 세력 평단 {'위' if cp > vwap else '아래'}")
        st.write(f"{'✅' if roe > 10 else '⚠️'} **지속성:** ROE {roe:.1f}%")
        st.write(f"{'✅' if 35 < float(curr['RSI']) < 65 else '⚠️'} **심리:** RSI {float(curr['RSI']):.1f}")
        st.write("---")
        st.subheader("📝 투자 가이드")
        if sc >= 80: st.success("🚀 강력 매수 구간")
        elif sc >= 60: st.info("⚖️ 관망 및 분할 대응")
        else: st.error("⏳ 진입 금지/위험")
        st.caption(f"동기화: {datetime.now().strftime('%H:%M:%S')}")
else:
    st.warning("⚠️ API 한도 초과 상태입니다. 잠시 후 새로고침 해주세요.")
