import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 캐시 강제 분리 (안전장치)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# [핵심] 데이터 호출 실패 시 빈 값이라도 돌려주어 화면 멈춤 방지
@st.cache_data(ttl=300) 
def safe_fetch_data(ticker, period, interval):
    try:
        return yf.Ticker(ticker).history(period=period, interval=interval)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def safe_fetch_info(ticker):
    try:
        return yf.Ticker(ticker).info
    except:
        return {}

# 2. 지능형 실시간 검색 (오류 방지형)
@st.cache_data(ttl=86400)
def hybrid_search(query):
    if not query: return None
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR&quotesCount=1"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        if res.get('quotes'): return res['quotes'][0]['symbol']
    except: pass
    return query

# --- 사이드바: 슬림 디자인 ---
with st.sidebar:
    st.header("🚀 퀵 메뉴")
    c1, c2 = st.columns(2)
    if c1.button("엔비디아"): st.session_state['search'] = "NVDA"
    if c1.button("파마리서치"): st.session_state['search'] = "214450.KQ"
    if c2.button("팔란티어"): st.session_state['search'] = "PLTR"
    if c2.button("휴림로봇"): st.session_state['search'] = "090710.KQ"
    
    st.write("---")
    search_input = st.text_input("종목명/티커", value=st.session_state.get('search', ""))
    my_price = st.number_input("나의 평단", value=0.0)
    # [강력 조치] 무반응 방지를 위해 버튼 클릭 시에만 실행되도록 완전 고정
    btn_label = "📊 분석 시작" if not st.session_state.get('loading') else "⏳ 분석 중..."
    is_ready = st.button(btn_label)

# --- 메인 분석 화면 ---
if is_ready and search_input:
    ticker = hybrid_search(search_input)
    if ticker:
        # 차트 주기 슬림 드롭다운
        int_labels = {"1분": "1m", "5분": "5m", "10분": "10m", "1일": "1d"}
        per_labels = {"1분": "1d", "5분": "5d", "10분": "5d", "1일": "1y"}
        
        col_s, _ = st.columns([1.5, 4])
        with col_s:
            sel_int = st.selectbox("⏱️ 주기 선택", list(int_labels.keys()), index=3)

        with st.spinner('서버 연결 중...'):
            data = safe_fetch_data(ticker, per_labels[sel_int], int_labels[sel_int])
            info = safe_fetch_info(ticker)
        
        if not data.empty:
            st.title(f"🛡️ {info.get('longName', search_input)}")
            
            # 메트릭 표시 (데이터 없을 시 0 처리)
            curr_p = data['Close'].iloc[-1]
            roe = info.get('returnOnEquity', 0) * 100
            
            m1, m2, m3 = st.columns(3)
            m1.metric("📈 현재가", f"{curr_p:,.2f}")
            m2.metric("🎯 ROE", f"{roe:.1f}%")
            m3.metric("📊 부채", f"{info.get('debtToEquity', 0):.1f}%")

            # 차트
            fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            st.success(f"✅ 분석 완료 ({datetime.now().strftime('%H:%M:%S')})")
        else:
            st.error("앗! 데이터 수신에 실패했습니다. 1분만 쉬었다가 다시 눌러주세요.")
else:
    st.info("왼쪽 검색창에 종목을 넣고 [📊 분석 시작] 버튼을 눌러주세요! 😊")
