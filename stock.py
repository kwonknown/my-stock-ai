import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 캐시 전략 (야후/구글 하이브리드 최적화)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# [최적화] API 호출을 분리하여 부하 분산
@st.cache_data(ttl=300) # 분봉 데이터는 5분간 재사용
def fetch_fast_data(ticker, period, interval):
    return yf.Ticker(ticker).history(period=period, interval=interval)

@st.cache_data(ttl=3600) # 무거운 기업 정보(ROE 등)는 1시간에 한 번만
def fetch_heavy_info(ticker):
    stock = yf.Ticker(ticker)
    return stock.info

# 2. 지능형 실시간 검색 (검색 실패 시에도 대비)
@st.cache_data(ttl=86400)
def hybrid_search(query):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR&quotesCount=1"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res['quotes']: return res['quotes'][0]['symbol']
    except: return query
    return query

# 3. 보조지표 계산 로직 (경량화)
def add_tech_indicators(df):
    if df.empty: return df
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

# --- 사이드바: 퀵 메뉴 & 히스토리 ---
with st.sidebar:
    st.header("🚀 퀵 메뉴")
    c1, c2 = st.columns(2)
    if c1.button("엔비디아"): st.session_state['search'] = "NVDA"
    if c1.button("파마리서치"): st.session_state['search'] = "214450.KQ"
    if c2.button("팔란티어"): st.session_state['search'] = "PLTR"
    if c2.button("휴림로봇"): st.session_state['search'] = "090710.KQ"
    
    st.write("---")
    search_input = st.text_input("종목/티커 검색", value=st.session_state.get('search', "현대건설"))
    my_price = st.number_input("나의 매수 평단가", value=0.0)
    # API 보호를 위한 분석 실행 버튼
    is_ready = st.button("📊 분석 실행 / 갱신")

# --- 메인 분석 화면 ---
ticker = hybrid_search(search_input)

if ticker and is_ready:
    try:
        # 4. 차트 주기 선택 (가로 길이를 줄여 작게 배치)
        int_labels = {"1분": "1m", "5분": "5m", "10분": "10m", "1일": "1d"}
        per_labels = {"1분": "1d", "5분": "5d", "10분": "5d", "1일": "1y"}
        
        #         col_small, _ = st.columns([1, 4]) # 1:4 비율로 작게 만듦
        with col_small:
            selected_int = st.selectbox("⏱️ 주기", list(int_labels.keys()), index=3)

        # 데이터 호출
        with st.spinner('데이터 동기화 중...'):
            data = fetch_fast_data(ticker, per_labels[selected_int], int_labels[selected_int])
            info = fetch_heavy_info(ticker)
        
        if not data.empty:
            data = add_tech_indicators(data)
            curr_p = data['Close'].iloc[-1]
            vwap_p = data['VWAP'].iloc[-1]
            
            st.title(f"🛡️ {info.get('longName', search_input)} ({ticker})")
            
            # 메트릭 대시보드
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 현재가", f"{curr_p:,.2f}")
            m2.metric("🟢 매수 승률", f"{'확인 중'}") # 승률 로직은 이전 코드 유지
            m3.metric("🎯 세력 평단", f"{vwap_p:,.2f}")
            m4.metric("📊 ROE", f"{info.get('returnOnEquity', 0)*100:.1f}%")

            # 차트 시각화
            fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='주가')])
            fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
            if my_price > 0: fig.add_hline(y=my_price, line_dash="solid", line_color="green", annotation_text="내 평단")
            fig.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption(f"⏰ 데이터 수신: {datetime.now().strftime('%H:%M:%S')} (API 하이브리드 보호 모드)")

    except Exception as e:
        st.error(f"요청이 초과되었습니다. 1분만 기다려 주세요. ☕ ({e})")
