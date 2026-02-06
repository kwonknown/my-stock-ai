import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 캐시 (10분 단위 갱신)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

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

# 3. 지표 계산
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

# 4. [핵심] 엄격한 추세 확증 승률 로직
def calculate_strict_score(curr, info):
    curr_price = float(curr['Close'])
    vwap_val = float(curr['VWAP'])
    ma20_val = float(curr['MA20'])
    rsi_val = float(curr['RSI'])
    roe_val = info.get('returnOnEquity', 0) * 100
    
    # [조건 1] 하락 추세 종목 즉시 컷오프 (80% 절대 불가)
    # 주가가 20일선 '또는' 세력 평단 아래에 있으면 무조건 50점 이하
    if curr_price < vwap_val or curr_price < ma20_val:
        return 40  
    
    # [조건 2] 안정권 진입 (기본 점수 70점 시작)
    score = 70
    
    # [조건 3] 정배열 가점 (주가 > 20일선 > VWAP) - 안정적으로 올라가는 형태
    if curr_price > ma20_val > vwap_val:
        score += 15
        
    # [조건 4] 에너지 확인 (MACD 골든크로스)
    if float(curr['MACD']) > float(curr['Signal']):
        score += 5
        
    # [조건 5] 과열 제어 (너무 오르면 점수 깎기)
    if rsi_val > 70:
        score -= 20  # 추격 매수 방지
    elif 45 < rsi_val < 65:
        score += 10  # 가장 예쁘게 올라가는 구간
        
    return min(max(score, 0), 100)

# --- 사이드바 ---
st.sidebar.header("🔍 글로벌 마켓 스캔")
search_query = st.sidebar.text_input("종목명 입력", "삼성전자")
my_avg_price = st.sidebar.number_input("나의 매수 평단가", value=0.0)
ticker = get_ticker_pro(search_query)

if st.sidebar.button("💎 진짜 우량주 전수 조사 (80% 이상만)"):
    watchlist = ["AAPL", "NVDA", "TSLA", "PLTR", "005930.KS", "000660.KS", "000720.KS", "214450.KQ", "IONQ", "AMD", "MSFT", "GOOGL"]
    with st.sidebar:
        with st.spinner('안정적 우상향 종목 찾는 중...'):
            for t in watchlist:
                try:
                    s = yf.Ticker(t)
                    d = calculate_indicators(s.history(period="2mo"))
                    sc = calculate_strict_score(d.iloc[-1], s.info)
                    if sc >= 80:
                        st.write(f"🚀 **{t}** (승률:{sc}%)")
                        st.caption(f"안정적 추세 확정 구간")
                except: continue

# --- 메인 대시보드 ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")

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
            
            # 엄격한 승률 계산 적용
            buy_score = calculate_strict_score(curr, info)
            
            st.header(f"{info.get('longName', search_query)} ({ticker})")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 현재가", f"{curr_price:,.2f}")
            m2.metric("🟢 매수 승률", f"{buy_score}%")
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
                fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='orange'), name='20일선'))
                if my_avg_price > 0:
                    fig.add_hline(y=my_avg_price, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=550, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader("🔍 안정성 진단")
                if buy_score >= 80:
                    st.success("💎 **진입 적기:** 데이터상 완벽한 정배열 우상향 구간입니다.")
                elif buy_score <= 40:
                    st.error("⚠️ **진입 금지:** 추세가 꺾였거나 평단 아래에 있어 위험합니다.")
                else:
                    st.info("⚖️ **관망:** 추세 회복을 기다려야 하는 중립 구간입니다.")

                st.write("---")
                st.subheader("📊 재무 & 정보")
                st.write(f"**이익 지속성:** {'상급' if roe_val > 10 else '보통'}")
                st.write(f"**부채비율:** {info.get('debtToEquity', 0):.1f}%")
                st.caption(f"최종 업데이트: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        st.error(f"분석 오류: {e}")
