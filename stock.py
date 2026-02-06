import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 스마트 캐싱 (API 보호 모드)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

@st.cache_data(ttl=600) # 주가 데이터 10분 보관
def fetch_stock_data(ticker, period, interval):
    try:
        return yf.Ticker(ticker).history(period=period, interval=interval)
    except: return pd.DataFrame()

@st.cache_data(ttl=3600) # 무거운 기업 정보 1시간 보관
def fetch_stock_info(ticker):
    try:
        return yf.Ticker(ticker).info
    except: return {}

# 2. 지능형 검색 (한글 대응)
@st.cache_data(ttl=86400)
def hybrid_search(query):
    if not query: return None
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR&quotesCount=1"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        if res.get('quotes'): return res['quotes'][0]['symbol']
    except: pass
    return query

# 3. 보조지표 및 엄격한 승률 로직 (복구)
def calculate_all_metrics(df, info):
    if df.empty: return df, 0, []
    
    # 지표 계산
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    curr = df.iloc[-1]
    curr_p, vwap_p, ma20_p, rsi_v = float(curr['Close']), float(curr['VWAP']), float(curr['MA20']), float(curr['RSI'])
    
    # 5대 지표 체크리스트 가이드
    guides = []
    score = 40 if (curr_p < vwap_p or curr_p < ma20_p) else 70
    
    if curr_p > vwap_p: guides.append("✅ **수급(VWAP):** 세력 평단 위 지지 중")
    else: guides.append("❌ **수급(VWAP):** 세력 평단 아래 저항")
    
    if curr_p > ma20_p: guides.append("✅ **추세:** 20일선 위 안착")
    else: guides.append("❌ **추세:** 20일선 아래")
    
    if 35 < rsi_v < 65: 
        score += 10; guides.append(f"✅ **과열도(RSI:{rsi_v:.1f}):** 적정 수준")
    else: guides.append(f"⚠️ **과열도(RSI:{rsi_v:.1f}):** 주의 구간")
    
    if curr_p > ma20_p > vwap_p: score += 15 # 정배열 가점
    
    return df, min(max(score, 0), 100), guides

# --- 사이드바 ---
with st.sidebar:
    st.header("🚀 퀵 메뉴")
    c1, c2 = st.columns(2)
    if c1.button("엔비디아"): st.session_state['search'] = "NVDA"
    if c1.button("팔란티어"): st.session_state['search'] = "PLTR"
    if c2.button("파마리서치"): st.session_state['search'] = "214450.KQ"
    if c2.button("휴림로봇"): st.session_state['search'] = "090710.KQ"
    
    st.write("---")
    search_q = st.text_input("종목명/티커", value=st.session_state.get('search', ""))
    my_price = st.number_input("나의 평단", value=0.0)
    is_go = st.button("📊 분석 실행")

# --- 메인 화면 ---
if is_go and search_q:
    ticker = hybrid_search(search_q)
    if ticker:
        # 슬림 드롭다운
        int_map = {"1분": "1m", "5분": "5m", "10분": "10m", "1일": "1d"}
        per_map = {"1분": "1d", "5분": "5d", "10분": "5d", "1일": "1y"}
        
        c_sel, _ = st.columns([1.5, 4])
        with c_sel: sel_int = st.selectbox("⏱️ 주기", list(int_map.keys()), index=3)

        with st.spinner('데이터 동기화 중...'):
            data = fetch_stock_data(ticker, per_map[sel_int], int_map[sel_int])
            info = fetch_stock_info(ticker)
        
        if not data.empty:
            data, buy_score, guides = calculate_all_metrics(data, info)
            curr_p = data['Close'].iloc[-1]
            roe = info.get('returnOnEquity', 0) * 100
            
            st.title(f"🛡️ {info.get('longName', search_q)} ({ticker})")
            
            # 메트릭 대시보드
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 현재가", f"{curr_p:,.2f}")
            m2.metric("🟢 매수 승률", f"{buy_score}%")
            m3.metric("🎯 세력 평단", f"{data['VWAP'].iloc[-1]:,.2f}")
            m4.metric("📊 ROE", f"{roe:.1f}%")

            col_left, col_right = st.columns([2, 1])
            with col_left:
                fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
                if my_price > 0: fig.add_hline(y=my_price, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col_right:
                # 1. 지속 가능성 진단
                st.subheader("🔍 지속 가능성")
                if roe > 10: st.success(f"💎 **이익 지속성 상급:** ROE {roe:.1f}%")
                else: st.info(f"⚖️ **이익 지속성 보통:** 재무 건전성 확인 필요")
                
                # 2. 5대 지표 분석
                st.subheader("📝 상세 지표 분석")
                for g in guides: st.markdown(g)
                
                # 3. 매수매도 전망 & 가이드
                st.write("---")
                st.subheader("💡 투자 판단")
                if buy_score >= 80: st.success("🚀 **강력 매수 구간**")
                elif buy_score <= 40: st.error("⚠️ **관망/위험 관리 시점**")
                else: st.info("⚖️ **중립 구간**")
                
                if my_price > 0:
                    p_rate = ((curr_p - my_price) / my_price) * 100
                    if p_rate > 5: st.warning("🔥 **스윙 팁:** 수익권 익절 고려")
                    elif curr_p <= data['VWAP'].iloc[-1] * 1.02: st.success("💎 **스윙 팁:** 세력 평단 지지 매수")

    except Exception as e: st.error(f"오류: {e}")
