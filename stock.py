import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 세션 상태 초기화
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'search' not in st.session_state:
    st.session_state['search'] = "000660.KS"  # 기본값을 하이닉스로 설정

# 2. 캐시된 데이터 호출 함수 (부하 방지)
@st.cache_data(ttl=600)
def get_stock_data(ticker, period, interval):
    try:
        return yf.Ticker(ticker).history(period=period, interval=interval)
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_stock_info(ticker):
    try:
        return yf.Ticker(ticker).info
    except: return {}

# 3. 지능형 검색 및 지표 계산
def calculate_indicators(df):
    if df.empty: return df
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    return df

# [조율된 유연한 승률 로직] 하이닉스 같은 우상향주 포착용
def calculate_flexible_score(curr, info):
    try:
        curr_p, vwap_p, ma20_p = float(curr['Close']), float(curr['VWAP']), float(curr['MA20'])
        rsi_v = float(curr['RSI'])
        
        # 20일선 위에만 있다면 일단 70점 후보군 (VWAP 아래여도 즉시 탈락시키지 않음)
        if curr_p < ma20_p: return 40
        
        score = 70
        if curr_p > vwap_p: score += 15  # 세력 평단 위일 때 가점
        if 40 < rsi_v < 70: score += 15  # 적정 심리 구간 가점
        
        # 재무 가점 (ROE가 높으면 추가 점수)
        roe = info.get('returnOnEquity', 0) * 100
        if roe > 20: score += 5
            
        return min(max(score, 0), 100)
    except: return 50

# --- 사이드바: 미래 지향적 섹터 메뉴 & 고속 스캐너 ---
with st.sidebar:
    st.header("🚀 미래 산업 섹터")
    
    # [종목 확장] 비만치료제, AI인프라, 우주 등 추가
    with st.expander("💻 AI 반도체 & 인프라", expanded=True):
        c1, c2 = st.columns(2)
        if c1.button("하이닉스"): st.session_state['search'] = "000660.KS"; st.rerun()
        if c1.button("엔비디아"): st.session_state['search'] = "NVDA"; st.rerun()
        if c2.button("버티브(VRT)"): st.session_state['search'] = "VRT"; st.rerun()
        if c2.button("마이크론"): st.session_state['search'] = "MU"; st.rerun()

    with st.expander("🧪 바이오 & 비만치료"):
        c1, c2 = st.columns(2)
        if c1.button("파마리서치"): st.session_state['search'] = "214450.KQ"; st.rerun()
        if c1.button("일라이릴리"): st.session_state['search'] = "LLY"; st.rerun()
        if c2.button("노보노디스크"): st.session_state['search'] = "NVO"; st.rerun()
        if c2.button("유한양행"): st.session_state['search'] = "000100.KS"; st.rerun()

    with st.expander("🛡️ 방산 & 🤖 로봇"):
        c1, c2 = st.columns(2)
        if c1.button("한화에어로"): st.session_state['search'] = "012450.KS"; st.rerun()
        if c1.button("현대로템"): st.session_state['search'] = "064350.KS"; st.rerun()
        if c2.button("레인보우"): st.session_state['search'] = "277810.KQ"; st.rerun()
        if c2.button("휴림로봇"): st.session_state['search'] = "090710.KQ"; st.rerun()

    st.write("---")
    # [고성능 배치 스캐너] 미래 종목 포함 30개 스캔
    if st.button("💎 승률 80%↑ 글로벌 보석 발굴"):
        scan_list = [
            "AAPL", "MSFT", "NVDA", "TSLA", "PLTR", "LLY", "NVO", "VRT", "AMD", "AVGO", "COST",
            "005930.KS", "000660.KS", "005380.KS", "214450.KQ", "012450.KS", "277810.KQ", "090710.KQ"
        ]
        with st.spinner('초고속 글로벌 전수 조사 중...'):
            # 배치 다운로드로 API 과부하 방지
            all_d = yf.download(scan_list, period="1mo", interval="1d", group_by='ticker', threads=True)
            for t in scan_list:
                try:
                    d = calculate_indicators(all_d[t].dropna())
                    score = calculate_flexible_score(d.iloc[-1], {})
                    if score >= 80:
                        if st.button(f"🎯 {t} ({score}%)", key=f"sc_{t}"):
                            st.session_state['search'] = t; st.rerun()
                except: continue

    st.write("---")
    # 히스토리 복구 (클릭 시 즉시 이동)
    if st.session_state['history']:
        st.subheader("🕒 최근 본 종목")
        for h in st.session_state['history']:
            if st.button(f"📜 {h}", key=f"h_{h}"):
                st.session_state['search'] = h; st.rerun()

    st.write("---")
    search_q = st.text_input("종목명/티커 입력", value=st.session_state['search'])
    my_p = st.number_input("나의 평단가", value=0.0)
    if st.button("📊 분석 실행"):
        st.session_state['search'] = search_q; st.rerun()

# --- 메인 로직 ---
ticker = st.session_state['search']
if ticker:
    if ticker not in st.session_state['history']:
        st.session_state['history'].insert(0, ticker)
        st.session_state['history'] = st.session_state['history'][:5]

    # 주기 설정 (슬림 드롭다운)
    int_map = {"1분": "1m", "5분": "5m", "1일": "1d"}
    c_sel, _ = st.columns([1.5, 4])
    with c_sel: sel_int = st.selectbox("⏱️ 주기", list(int_map.keys()), index=2)

    data = get_stock_data(ticker, "1y" if sel_int=="1일" else "5d", int_map[sel_int])
    info = get_stock_info(ticker)
    
    if not data.empty:
        data = calculate_indicators(data)
        curr_p = data['Close'].iloc[-1]
        buy_score = calculate_flexible_score(data.iloc[-1], info)
        
        st.title(f"🛡️ {info.get('longName', ticker)} ({ticker})")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📈 현재가", f"{curr_p:,.2f}")
        m2.metric("🟢 매수 승률", f"{buy_score}%")
        m3.metric("🎯 세력 평단", f"{data['VWAP'].iloc[-1]:,.2f}")
        m4.metric("📊 ROE", f"{info.get('returnOnEquity', 0)*100:.1f}%")

        col_l, col_r = st.columns([2, 1])
        with col_l:
            fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
            fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
            if my_p > 0: fig.add_hline(y=my_p, line_dash="solid", line_color="green")
            fig.update_layout(height=450, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig, use_container_width=True)
            
        with col_r:
            st.subheader("🔍 지속 가능성")
            roe = info.get('returnOnEquity', 0) * 100
            if roe > 10: st.success(f"💎 **상급:** ROE {roe:.1f}%")
            else: st.info("⚖️ **보통:** 재무 확인 필요")
            
            st.write("---")
            st.subheader("💡 투자 가이드")
            if buy_score >= 80: st.success("🚀 **안정적 우상향 진입 구간**")
            elif buy_score <= 40: st.error("⚠️ **추세 이탈 주의 구간**")
            else: st.info("⚖️ **에너지 응축 중**")
            st.caption(f"동기화: {datetime.now().strftime('%H:%M:%S')}")
