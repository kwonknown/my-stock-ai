import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. 앱 설정 및 캐시 최적화
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

if 'selected_stock' not in st.session_state:
    st.session_state['selected_stock'] = "삼성전자"

# API 한도 보호를 위해 캐시 시간을 300초(5분)로 상향
@st.cache_data(ttl=300)
def get_safe_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if df.empty: return None, None
        # 실시간 가격 보정은 꼭 필요할 때만 호출
        info = stock.info
        return df, info
    except:
        return None, None

# 2. 지표 계산 및 승률 로직 (우리가 완성했던 그 로직!)
def calculate_metrics(df, info):
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
    
    # 보수적 승률 로직
    if cp < vwap and cp < ma: sc = 35
    else:
        sc = 70
        if cp > vwap: sc += 10
        if cp > ma: sc += 10
        if 40 < rsi < 65: sc += 10
    return df, min(sc, 100)

# --- 사이드바 ---
st.sidebar.header("📡 글로벌 마켓 엔진")
input_q = st.sidebar.text_input("종목명 입력", value=st.session_state['selected_stock'])

if st.sidebar.button("🔄 강제 새로고침 (주의)"):
    st.cache_data.clear()
    st.rerun()

# --- 메인 분석 화면 ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")

# 검색창 동기화
if input_q != st.session_state['selected_stock']:
    st.session_state['selected_stock'] = input_q

ticker = st.session_state['selected_stock']
data_raw, info = get_safe_data(ticker)

if data_raw is not None:
    data, sc = calculate_metrics(data_raw, info)
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
        st.subheader("🔍 상세 지표 진단")
        st.write(f"{'✅' if cp > vwap else '❌'} **수급:** 세력 평단 {'위' if cp > vwap else '아래'}")
        st.write(f"{'✅' if roe > 10 else '⚠️'} **지속성:** ROE {roe:.1f}%")
        st.write("---")
        st.subheader("📝 투자 가이드")
        if sc >= 80: st.success("🚀 강력 매수 구간")
        elif sc >= 60: st.info("⚖️ 관망 및 분할 대응")
        else: st.error("⏳ 진입 금지/위험")
        st.caption(f"동기화: {datetime.now().strftime('%H:%M:%S')}")
else:
    st.warning("⚠️ 호출 한도 초과 또는 데이터 없음. 1분 뒤 새로고침 버튼을 눌러주세요.")
