import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 캐시 고도화
st.set_page_config(page_title="kwonknown AI Master", layout="wide")
if 'history' not in st.session_state: st.session_state['history'] = []

# [최적화] 주기별로 캐시 시간을 다르게 적용하여 API 호출 최소화
@st.cache_data(ttl=120) # 분봉 데이터는 2분간 보관
def get_intraday_data(ticker, period, interval):
    return yf.Ticker(ticker).history(period=period, interval=interval)

@st.cache_data(ttl=3600) # 일봉 데이터 및 기업 정보는 1시간 동안 보관
def get_static_info(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="1y"), stock.info

# 2. 지능형 검색 엔진 (캐시 적용)
@st.cache_data(ttl=86400) # 티커 매핑은 하루에 한 번만
def get_ticker_pro(query):
    mapping = {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "팔란티어": "PLTR", "테슬라": "TSLA"}
    if query in mapping: return mapping[query]
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR&quotesCount=1"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res['quotes']: return res['quotes'][0]['symbol']
    except: return None
    return query

# 3. 보조지표 계산 (이전과 동일)
def calculate_indicators(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    return df

# --- 사이드바 ---
with st.sidebar:
    st.header("🚀 퀵 메뉴")
    cols = st.columns(2)
    with cols[0]:
        if st.button("엔비디아"): st.session_state['search'] = "NVDA"
        if st.button("파마리서치"): st.session_state['search'] = "214450.KQ"
    with cols[1]:
        if st.button("팔란티어"): st.session_state['search'] = "PLTR"
        if st.button("휴림로봇"): st.session_state['search'] = "090710.KQ"
    
    st.write("---")
    search_query = st.text_input("종목명/티커 검색", value=st.session_state.get('search', "현대건설"))
    my_avg_price = st.number_input("나의 매수 평단가", value=0.0)
    
    # [중요] API 아끼기 위한 실행 버튼
    run_analysis = st.button("📊 분석 실행 / 새로고침")

# --- 메인 로직 ---
ticker = get_ticker_pro(search_query)

if ticker and run_analysis:
    if ticker not in st.session_state['history']:
        st.session_state['history'].insert(0, ticker)
        st.session_state['history'] = st.session_state['history'][:5]
    
    try:
        # 주기 설정
        interval_map = {"1분": "1m", "5분": "5m", "10분": "10m", "1일": "1d"}
        period_map = {"1분": "1d", "5분": "5d", "10분": "5d", "1일": "1y"}
        
        selected_interval = st.selectbox("차트 주기", list(interval_map.keys()), index=3)
        
        # 데이터 호출 (분봉/일봉에 따라 다른 캐시 함수 사용)
        if selected_interval == "1일":
            data, info = get_static_info(ticker)
        else:
            _, info = get_static_info(ticker)
            data = get_intraday_data(ticker, period_map[selected_interval], interval_map[selected_interval])
        
        if not data.empty:
            data = calculate_indicators(data)
            curr = data.iloc[-1]
            curr_price, vwap_val = float(curr['Close']), float(curr['VWAP'])
            roe_val = info.get('returnOnEquity', 0) * 100
            
            st.title(f"🛡️ {info.get('longName', search_query)} ({ticker})")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 현재가", f"{curr_price:,.2f}")
            # 승률 계산은 추세 확증 로직 적용 (생략)
            m3.metric("🎯 세력 평단", f"{vwap_val:,.2f}")
            m4.metric("📊 ROE", f"{roe_val:.1f}%")

            fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
            fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
            if my_avg_price > 0: fig.add_hline(y=my_avg_price, line_dash="solid", line_color="green")
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption(f"마지막 데이터 동기화: {datetime.now().strftime('%H:%M:%S')} (캐시 적용 중)")

    except Exception as e:
        st.error(f"요청이 너무 많습니다. 잠시 후 다시 시도해 주세요. ({e})")
