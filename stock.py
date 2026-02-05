import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 캐시
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# 클릭 시 종목 이동을 위한 세션 상태 초기화
if 'selected_stock' not in st.session_state:
    st.session_state['selected_stock'] = "삼성전자"

@st.cache_data(ttl=600)
def get_stock_data(ticker):
    return yf.Ticker(ticker).history(period="1y")

# 2. 검색 엔진
def get_ticker_pro(query):
    mapping = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS",
        "현대건설": "000720.KS", "기아": "000270.KS", "네이버": "035420.KS",
        "파마리서치": "214450.KQ", "팔란티어": "PLTR", "테슬라": "TSLA", "엔비디아": "NVDA"
    }
    if query in mapping: return mapping[query]
    if query.isdigit() and len(query) == 6: return f"{query}.KS"
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res['quotes']: return res['quotes'][0]['symbol']
    except: return None
    return query

# 3. 보조지표 계산
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
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

# 4. 보수적인 추세 확증 승률 로직 (강화됨)
def calculate_conservative_score(curr, info):
    curr_price = float(curr['Close'])
    vwap_val = float(curr['VWAP'])
    ma20_val = float(curr['MA20'])
    rsi_val = float(curr['RSI'])
    
    # [필터 1] 추세 미달 즉시 컷오프 (80% 절대 불가)
    if curr_price < vwap_val or curr_price < ma20_val:
        return 30  
    
    # [필터 2] 고점 과열 컷오프 (이격도가 너무 크면 80% 불가)
    # 평단 대비 15% 이상 급등한 경우 '조정 위험'으로 간주
    if curr_price > vwap_val * 1.15:
        return 60

    score = 70 # 기본 보수적 시작가
    
    # [가점 1] 정배열 유지 (주가 > 20일선 > VWAP)
    if curr_price > ma20_val > vwap_val: score += 10
        
    # [가점 2] 에너지 골든크로스
    if float(curr['MACD']) > float(curr['Signal']): score += 5
        
    # [가점 3] 보수적 심리 구간 (RSI 40~60 사이만 가점)
    if 40 < rsi_val < 60: score += 15
    elif rsi_val >= 65: score -= 10 # 65만 넘어도 경계 시작
        
    return min(max(score, 0), 100)

# --- 사이드바 ---
st.sidebar.header("🔍 마켓 스캐너")
# 검색창의 기본값을 세션 상태의 종목으로 설정
search_query = st.sidebar.text_input("종목명 입력", value=st.session_state['selected_stock'])
my_avg_price = st.sidebar.number_input("나의 매수 평단가", value=0.0)

if st.sidebar.button("💎 보수적 우량주 전수 조사"):
    watchlist = ["AAPL", "NVDA", "TSLA", "PLTR", "005930.KS", "000660.KS", "000720.KS", "214450.KQ", "IONQ", "AMD", "MSFT"]
    with st.sidebar:
        st.write("---")
        for t in watchlist:
            try:
                s = yf.Ticker(t)
                d = calculate_indicators(s.history(period="2mo"))
                sc = calculate_conservative_score(d.iloc[-1], s.info)
                if sc >= 80:
                    # 버튼 클릭 시 해당 종목으로 이동하게 함
                    if st.button(f"🚀 {t} (승률:{sc}%)", key=f"btn_{t}"):
                        st.session_state['selected_stock'] = t
                        st.rerun()
            except: continue

# --- 메인 대시보드 ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")

ticker = get_ticker_pro(st.session_state['selected_stock'] if search_query == st.session_state['selected_stock'] else search_query)

if ticker:
    try:
        stock_obj = yf.Ticker(ticker)
        data = get_stock_data(ticker)
        if not data.empty:
            data = calculate_indicators(data)
            info = stock_obj.info
            curr = data.iloc[-1]
            curr_price = float(curr['Close'])
            vwap_val = float(curr['VWAP'])
            roe_val = info.get('returnOnEquity', 0) * 100
            
            buy_score = calculate_conservative_score(curr, info)
            
            st.header(f"{info.get('longName', ticker)} ({ticker})")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 현재가", f"{curr_price:,.2f}")
            m2.metric("🟢 보수적 승률", f"{buy_score}%")
            if my_avg_price > 0:
                p_rate = ((curr_price - my_avg_price) / my_avg_price) * 100
                m3.metric("💰 나의 수익률", f"{p_rate:+.2f}%")
            else:
                m3.metric("🎯 세력 평단", f"{vwap_val:,.2f}")
            m4.metric("📊 ROE", f"{roe_val:.1f}%")

            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='주가')])
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
                if my_avg_price > 0:
                    fig.add_hline(y=my_avg_price, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader("🛡️ 보수적 추세 진단")
                if buy_score >= 80:
                    st.success("💎 **진입 적기:** 완벽하게 무릎 구간이며 추세가 확정되었습니다.")
                elif buy_score >= 60:
                    st.warning("⚠️ **고점 주의:** 추세는 좋으나 세력 평단과 너무 멀어졌습니다.")
                else:
                    st.error("⏳ **관망:** 하락 추세이거나 지지선 확인이 필요합니다.")

                st.write("---")
                st.subheader("💡 kwonknown 가이드")
                if my_avg_price > 0 and p_rate > 5 and float(curr['RSI']) > 65:
                    st.warning("🔥 **스윙 타이밍:** 수익 중일 때 비중을 줄이고 눌림목을 기다리세요!")

    except Exception as e:
        st.error(f"분석 오류: {e}")
