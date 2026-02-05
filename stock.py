import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 세션 상태 (이동 기능용)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")
if 'selected_stock' not in st.session_state: st.session_state['selected_stock'] = "삼성전자"

# 데이터 갱신 (1분 단위로 가격 지연 최소화)
@st.cache_data(ttl=60)
def get_stock_data_pro(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y")
    try:
        # 실시간 가격 보정
        real_price = stock.info.get('regularMarketPrice') or stock.fast_info.get('last_price')
        if real_price: df.iloc[-1, df.columns.get_loc('Close')] = real_price
    except: pass
    return df, stock.info

# 2. 보조지표 계산 로직 (상세 지표 복구용)
def calculate_all_indicators(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_High'] = df['MA20'] + (df['BB_std'] * 2)
    return df

# 3. 보수적+스마트 승률 로직
def get_smart_score(curr, info):
    cp = float(curr['Close']); vwap = float(curr['VWAP']); ma = float(curr['MA20'])
    rsi = float(curr['RSI']); roe = info.get('returnOnEquity', 0) * 100
    if cp < vwap and cp < ma: return 30 # 강력 컷오프
    score = 70
    if cp > vwap: score += 10
    if cp > ma: score += 10
    if 40 < rsi < 65: score += 10
    if roe > 15: score += 5
    return min(max(score, 0), 100)

# --- 사이드바: 글로벌 섹터 스캐너 ---
st.sidebar.header("📡 글로벌 마켓 엔진")
if st.sidebar.button("🔄 실시간 가격 동기화"):
    st.cache_data.clear()
    st.rerun()

my_avg = st.sidebar.number_input("나의 매수 평단가", value=0.0)

# 섹터별 리스트업
sectors = {
    "AI/반도체": ["NVDA", "AMD", "005930.KS", "000660.KS"],
    "빅테크": ["AAPL", "MSFT", "PLTR", "TSLA"],
    "바이오/우량": ["214450.KQ", "000720.KS", "035420.KS"]
}

if st.sidebar.button("💎 우량주 전수 조사"):
    with st.sidebar:
        for sec, tks in sectors.items():
            st.markdown(f"**[{sec}]**")
            for t in tks:
                try:
                    d_raw, s_info = get_stock_data_pro(t)
                    d = calculate_all_indicators(d_raw).iloc[-1]
                    sc = get_smart_score(d, s_info)
                    if sc >= 75:
                        if st.button(f"🚀 {t} ({sc}%)", key=f"btn_{t}"):
                            st.session_state['selected_stock'] = t
                            st.rerun()
                except: continue

# --- 메인 분석 화면 (상세 지표 모두 복구) ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")
input_q = st.sidebar.text_input("직접 검색", value=st.session_state['selected_stock'])
ticker = input_q # 매핑 함수는 지면상 생략, 티커 직접 입력 기준

if ticker:
    try:
        data, info = get_stock_data_pro(ticker)
        data = calculate_all_indicators(data)
        curr = data.iloc[-1]
        cp = float(curr['Close']); vwap = float(curr['VWAP']); ma = float(curr['MA20'])
        rsi = float(curr['RSI']); roe = info.get('returnOnEquity', 0) * 100
        sc = get_smart_score(curr, info)
        
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
            fig.update_layout(height=550, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.subheader("🔍 지속 가능성 진단")
            if roe > 10: st.success(f"💎 **이익 지속성 상급:** ROE {roe:.1f}% 우량주")
            else: st.warning(f"⚠️ **수익성 체크 필요**")
            
            st.write("---")
            st.subheader("📝 5대 지표 체크리스트") # 이 부분이 핵심 복구 포인트!
            st.write(f"{'✅' if cp > vwap else '❌'} **수급:** 세력 평단 {'위 지지' if cp > vwap else '아래 저항'}")
            st.write(f"{'✅' if cp > ma else '❌'} **추세:** 20일선 {'위 안착' if cp > ma else '아래 하락'}")
            st.write(f"{'✅' if 35 < rsi < 65 else '⚠️'} **심리:** RSI {rsi:.1f} ({'적정' if 35 < rsi < 65 else '주의'})")
            st.write(f"{'✅' if float(curr['MACD']) > float(curr['Signal']) else '❌'} **에너지:** MACD {'상승' if float(curr['MACD']) > float(curr['Signal']) else '하락'} 우위")
            st.write(f"{'✅' if cp < float(curr['BB_High']) else '⚠️'} **가격:** {'상승 여력 있음' if cp < float(curr['BB_High']) else '밴드 상단 과열'}")

            st.write("---")
            st.subheader("📊 기업 재무 상세")
            st.write(f"**부채비율:** {info.get('debtToEquity', 0):.1f}%")
            st.write(f"**시가총액:** {info.get('marketCap', 0)/1e12:.2f}T")
            st.caption(f"최종 업데이트: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e: st.error(f"분석 오류: {e}")
