import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 세션 상태(History 저장용) 초기화
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

if 'history' not in st.session_state:
    st.session_state['history'] = []

def add_to_history(symbol):
    if symbol not in st.session_state['history']:
        st.session_state['history'].insert(0, symbol)
        if len(st.session_state['history']) > 5:
            st.session_state['history'].pop()

@st.cache_data(ttl=600)
def get_stock_data(ticker):
    return yf.Ticker(ticker).history(period="1y")

# 2. 하이브리드 검색 엔진
def get_ticker_pro(query):
    mapping = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS",
        "현대건설": "000720.KS", "기아": "000270.KS", "네이버": "035420.KS",
        "파마리서치": "214450.KQ", "팔란티어": "PLTR", "테슬라": "TSLA", "엔비디아": "NVDA"
    }
    if query in mapping: return mapping[query]
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res['quotes']: return res['quotes'][0]['symbol']
    except: return None
    return query

# 3. 지표 및 엄격한 승률 로직 (단순화 방지 고정)
def calculate_indicators(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_High'] = df['MA20'] + (df['BB_std'] * 2)
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

def calculate_strict_score(curr, info):
    curr_price = float(curr['Close'])
    vwap_val = float(curr['VWAP'])
    ma20_val = float(curr['MA20'])
    rsi_val = float(curr['RSI'])
    
    # [엄격 필터] 20일선 또는 VWAP 아래는 무조건 40점 이하 (삼성전자 등 필터링)
    if curr_price < vwap_val or curr_price < ma20_val:
        return 40  
    
    score = 70 # 기본 안정권
    if curr_price > ma20_val > vwap_val: score += 15 # 정배열 가점
    if float(curr['MACD']) > float(curr['Signal']): score += 5 # 에너지 가점
    
    if rsi_val > 70: score -= 20 # 과열 감점
    elif 45 < rsi_val < 65: score += 10 # 최적 구간 가점
        
    return min(max(score, 0), 100)

# --- 사이드바: 바로가기 & 히스토리 ---
with st.sidebar:
    st.header("🚀 퀵 메뉴")
    
    # 1. 우량주 바로가기
    st.subheader("💎 주요 우량주")
    cols = st.columns(2)
    with cols[0]:
        if st.button("엔비디아"): st.session_state['search'] = "NVDA"
        if st.button("팔란티어"): st.session_state['search'] = "PLTR"
    with cols[1]:
        if st.button("파마리서치"): st.session_state['search'] = "214450.KQ"
        if st.button("현대건설"): st.session_state['search'] = "000720.KS"
    
    st.write("---")
    
    # 2. 최근 본 종목 (히스토리)
    st.subheader("🕒 히스토리 (최근 5)")
    for h_item in st.session_state['history']:
        if st.button(f"📜 {h_item}", key=f"hist_{h_item}"):
            st.session_state['search'] = h_item
            
    st.write("---")
    
    # 기본 검색창
    default_search = st.session_state.get('search', "현대건설")
    search_query = st.text_input("종목명/티커 검색", value=default_search)
    my_avg_price = st.number_input("나의 매수 평단가", value=0.0)
    
    if st.button("💎 80% 이상 우상향주 스캔"):
        watchlist = ["AAPL", "NVDA", "TSLA", "PLTR", "005930.KS", "000660.KS", "000720.KS", "214450.KQ"]
        for t in watchlist:
            try:
                s = yf.Ticker(t); d = calculate_indicators(s.history(period="2mo"))
                sc = calculate_strict_score(d.iloc[-1], s.info)
                if sc >= 80: st.write(f"✅ **{t}** ({sc}%)")
            except: continue

# --- 메인 로직 ---
ticker = get_ticker_pro(search_query)

if ticker:
    add_to_history(ticker)
    try:
        stock_obj = yf.Ticker(ticker); data = get_stock_data(ticker)
        if not data.empty:
            data = calculate_indicators(data); info = stock_obj.info
            curr = data.iloc[-1]; curr_price = float(curr['Close'])
            vwap_val = float(curr['VWAP']); roe_val = info.get('returnOnEquity', 0) * 100
            buy_score = calculate_strict_score(curr, info)
            
            st.title(f"🛡️ {info.get('longName', search_query)} ({ticker})")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 현재가", f"{curr_price:,.2f}")
            m2.metric("🟢 매수 승률", f"{buy_score}%")
            m3.metric("🎯 세력 평단", f"{vwap_val:,.2f}")
            m4.metric("📊 ROE", f"{roe_val:.1f}%")

            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
                fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='orange'), name='20일선'))
                if my_avg_price > 0: fig.add_hline(y=my_avg_price, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("🔍 추세 확증 진단")
                if buy_score >= 80: st.success("💎 **추세 확정:** 안정적 우상향 구간")
                elif buy_score <= 40: st.error("⚠️ **진입 금지:** 추세 이탈 및 위험 구간")
                else: st.info("⚖️ **중립:** 추세 회복 대기 중")
                st.write(f"**부채비율:** {info.get('debtToEquity', 0):.1f}%")
                st.caption(f"데이터 갱신: {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e: st.error(f"오류: {e}")
