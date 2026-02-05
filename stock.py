import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 세션 상태 관리
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# [중요] 선택된 종목을 추적하기 위한 세션 상태 초기화
if 'selected_stock' not in st.session_state:
    st.session_state['selected_stock'] = "삼성전자"

# 데이터 갱신을 위한 캐시 (1분)
@st.cache_data(ttl=60)
def get_stock_data_fast(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y")
    # 실시간 가격 보정 로직
    try:
        realtime_price = stock.info.get('regularMarketPrice') or stock.fast_info.get('last_price')
        if realtime_price:
            df.iloc[-1, df.columns.get_loc('Close')] = realtime_price
    except: pass
    return df, stock.info

# 2. 지능형 티커 검색 엔진
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

# 3. 보조지표 및 보수적 승률 계산
def calculate_indicators(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
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

def calculate_balanced_score(curr, info):
    cp = float(curr['Close']); vwap = float(curr['VWAP']); ma = float(curr['MA20'])
    rsi = float(curr['RSI']); roe = info.get('returnOnEquity', 0) * 100
    if cp < vwap * 0.98 and cp < ma * 0.98: return 35 # 추세 이탈 컷오프
    score = 65
    if cp > vwap: score += 10 #
    if cp > ma: score += 10
    if float(curr['MACD']) > float(curr['Signal']): score += 5
    if 35 < rsi < 65: score += 10 #
    if roe > 15: score += 5 #
    if cp > vwap * 1.2: score -= 15 # 고점 경계
    return min(max(score, 0), 100)

# --- 사이드바 ---
st.sidebar.header("📡 글로벌 마켓 엔진")

# [중요] 검색창의 value를 세션 상태와 연결
input_q = st.sidebar.text_input("종목명 입력", value=st.session_state['selected_stock'], key="main_search")

# 새로고침 버튼
if st.sidebar.button("🔄 실시간 가격 동기화"):
    st.cache_data.clear()
    st.rerun()

my_avg = st.sidebar.number_input("나의 매수 평단가", value=0.0)

# 섹터별 스캐너
sectors = {
    "AI/반도체": ["NVDA", "AMD", "AVGO", "005930.KS", "000660.KS"],
    "빅테크": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "PLTR"],
    "미래차/우량": ["TSLA", "005380.KS", "214450.KQ", "000720.KS"]
}

if st.sidebar.button("💎 글로벌 섹터 전수 조사"):
    with st.sidebar:
        for sec, tickers in sectors.items():
            st.markdown(f"**[{sec}]**")
            for t in tickers:
                try:
                    d_raw, s_info = get_stock_data_fast(t)
                    d = calculate_indicators(d_raw).iloc[-1]
                    sc = calculate_balanced_score(d, s_info)
                    if sc >= 75:
                        # 버튼 클릭 시 세션 상태를 변경하고 리런(Rerun)
                        if st.button(f"🚀 {t} ({sc}%)", key=f"btn_{t}"):
                            st.session_state['selected_stock'] = t
                            st.rerun() # 앱을 다시 실행하여 변경된 종목 반영
                except: continue

# --- 메인 분석 화면 ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")

# 입력창에 직접 쳤을 때도 세션 상태 동기화
if input_q != st.session_state['selected_stock']:
    st.session_state['selected_stock'] = input_q

ticker = get_ticker_pro(st.session_state['selected_stock'])

if ticker:
    try:
        data, info = get_stock_data_fast(ticker)
        if not data.empty:
            data = calculate_indicators(data)
            curr = data.iloc[-1]
            cp = float(curr['Close']); vwap = float(curr['VWAP']); ma = float(curr['MA20'])
            rsi = float(curr['RSI']); roe = info.get('returnOnEquity', 0) * 100
            sc = calculate_balanced_score(curr, info)
            
            st.header(f"{info.get('longName', ticker)} ({ticker})")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📈 보정 현재가", f"{cp:,.2f}")
            c2.metric("🟢 스마트 승률", f"{sc}%")
            if my_avg > 0:
                p_r = ((cp - my_avg) / my_avg) * 100
                c3.metric("💰 나의 수익률", f"{p_r:+.2f}%")
            else: c3.metric("🎯 세력 평단", f"{vwap:,.2f}")
            c4.metric("📊 ROE", f"{roe:.1f}%")

            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='주가')])
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
                fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='orange'), name='20일선'))
                if my_avg > 0: fig.add_hline(y=my_avg, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader("📝 상세 지표 분석")
                st.write(f"**수급:** {'✅ 세력 평단 위' if cp > vwap else '❌ 세력 평단 아래'}")
                st.write(f"**추세:** {'✅ 20일선 위' if cp > ma else '❌ 20일선 아래'}")
                st.write(f"**심리:** {rsi:.1f} ({'✅ 적정' if 35 < rsi < 65 else '⚠️ 주의'})")
                st.write("---")
                st.subheader("💡 투자 의견")
                if sc >= 80: st.success("💎 **강력 매수 진입**")
                elif sc >= 60: st.info("⚖️ **보유 및 관망**")
                else: st.error("⏳ **매수 금지/위험**")
                st.caption(f"최종 동기화: {datetime.now().strftime('%H:%M:%S')}")
                if my_avg > 0 and cp <= vwap * 1.02:
                    st.success("💎 **스윙 팁:** 세력 평단 부근 지지 중. 수량 확대 기회입니다!")

    except Exception as e: st.error(f"분석 오류: {e}")
