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
    st.session_state['search'] = "000660.KS"

# 2. 캐시된 데이터 호출 함수
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

# 3. 보조지표 계산 로직 (거래량 분석 추가)
def calculate_indicators(df):
    if df.empty: return df
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    # 거래량 이평선 (5일) 추가
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    return df

# [고도화된 유연한 승률 로직] 거래량 가산점 포함
def calculate_flexible_score(df, info):
    if df.empty: return 0, []
    try:
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        curr_p, vwap_p, ma20_p = float(curr['Close']), float(curr['VWAP']), float(curr['MA20'])
        rsi_v = float(curr['RSI'])
        
        guides = []
        # 20일선 위라면 기본 70점 후보군 (하이닉스 누락 방지)
        score = 70 if curr_p > ma20_p else 40
        
        if curr_p > vwap_p: 
            score += 10; guides.append("✅ **수급(VWAP):** 세력 평단 위 안정적 지지")
        else: 
            guides.append("⚠️ **수급(VWAP):** 세력 평단 근접 (눌림목 매수 기회)")
            
        if curr_p > ma20_p: guides.append("✅ **추세:** 20일선 위 우상향 지속")
        else: guides.append("❌ **추세:** 20일선 아래 이탈 (관망 필요)")
        
        # 거래량 보너스 (전일 대비 1.5배 또는 5일 평균 대비 급증 시)
        vol_increase = curr['Volume'] / prev['Volume']
        if vol_increase > 1.5:
            score += 5; guides.append(f"🔥 **거래량:** 전일 대비 {vol_increase:.1f}배 급증! (돈 유입)")
            
        if 40 < rsi_v < 70: 
            score += 10; guides.append(f"✅ **심리(RSI:{rsi_v:.1f}):** 과열 없는 적정 구간")
        elif rsi_v >= 70:
            score -= 10; guides.append(f"🔥 **심리(RSI:{rsi_v:.1f}):** 단기 과열 주의")
            
        # 정배열 가점
        if curr_p > ma20_p > vwap_p: score += 5
            
        return min(max(score, 0), 100), guides
    except: return 50, []

# --- 사이드바 ---
with st.sidebar:
    st.header("🚀 미래 산업 섹터")
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

    st.write("---")
    if st.button("💎 승률 80%↑ 글로벌 보석 발굴"):
                # [초강력 확장판] 글로벌 전수 조사 리스트 (약 70여 종목)
        scan_list = [
            # 1. 미국 빅테크 & AI 반도체 (The Mag 7 & Semi)
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", 
            "AVGO", "AMD", "MU", "INTC", "QCOM", "AMAT", "LRCX", "ARM", "SMCI", "ASML",
            
            # 2. 소프트웨어 & 성장주 (SaaS & AI Services)
            "PLTR", "ADBE", "CRM", "NOW", "SNOW", "NET", "PANW", "IONQ", "SOUN",
            
            # 3. 비만치료제 & 헬스케어 (GLP-1 & Biotech)
            "LLY", "NVO", "VRTX", "AMGN", "ISRG", "PFE", "MRK",
            
            # 4. 미국 인프라 & 소비재 (Infrastructure & Consumer)
            "VRT", "COST", "NFLX", "WMT", "KO", "PEP", "XOM", "CAT", "GE", "UBER", "ABNB",
            
            # 5. 국내 반도체 & IT (K-Semicon & Tech)
            "005930.KS", "000660.KS", "000990.KS", "042700.KQ", "035420.KS", "035720.KS",
            
            # 6. 국내 바이오 & 뷰티 (K-Bio & Aesthetic) - 파마리서치 등
            "214450.KQ", "000100.KS", "068270.KS", "277470.KS", "090430.KS", "192080.KS",
            
            # 7. 국내 방산 & 자동차 & 로봇 (K-Defense, Auto & Robot)
            "012450.KS", "064350.KS", "005380.KS", "000270.KS", "277810.KQ", "090710.KQ", "040910.KQ",
            
            # 8. 국내 자원 & 금융 (K-Resource & Finance)
            "005490.KS", "010130.KS", "055550.KS", "105560.KS", "000720.KS"
        ]

        with st.spinner('전수 조사 중...'):
            all_d = yf.download(scan_list, period="1mo", interval="1d", group_by='ticker', threads=True)
            for t in scan_list:
                try:
                    d = calculate_indicators(all_d[t].dropna())
                    score, _ = calculate_flexible_score(d, {})
                    if score >= 80:
                        if st.button(f"🎯 {t} ({score}%)", key=f"sc_{t}"):
                            st.session_state['search'] = t; st.rerun()
                except: continue

    st.write("---")
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

# --- 메인 화면 ---
ticker = st.session_state['search']
if ticker:
    if ticker not in st.session_state['history']:
        st.session_state['history'].insert(0, ticker)
        st.session_state['history'] = st.session_state['history'][:5]

    int_map = {"1분": "1m", "5분": "5m", "1일": "1d"}
    c_sel, _ = st.columns([1.5, 4])
    with c_sel: sel_int = st.selectbox("⏱️ 주기 선택", list(int_map.keys()), index=2)

    data = get_stock_data(ticker, "1y" if sel_int=="1일" else "5d", int_map[sel_int])
    info = get_stock_info(ticker)
    
    if not data.empty:
        data = calculate_indicators(data)
        buy_score, guides = calculate_flexible_score(data, info)
        curr_p = data['Close'].iloc[-1]
        
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
            fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='orange'), name='20일선'))
            if my_p > 0: fig.add_hline(y=my_p, line_dash="solid", line_color="green", annotation_text="내 평단")
            fig.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig, use_container_width=True)
            
        with col_r:
            st.subheader("🔍 지속 가능성 진단")
            roe = info.get('returnOnEquity', 0) * 100
            if roe > 20: st.success(f"💎 **초우량 지속성:** ROE {roe:.1f}%")
            elif roe > 10: st.success(f"✅ **안정적 지속성:** ROE {roe:.1f}%")
            else: st.info(f"⚖️ **성장성 체크:** ROE {roe:.1f}%")
            
            st.subheader("📝 상세 지표 분석")
            for g in guides: st.markdown(g)
            
            st.write("---")
            st.subheader("💡 kwonknown 스윙 가이드")
            if buy_score >= 80: st.success("🚀 **강력 매수 구간 (승률 80%↑)**")
            elif buy_score >= 60: st.warning("⚖️ **분할 매수 구간**")
            else: st.error("⏳ **관망/위험 관리 시점**")
            
            if my_p > 0:
                p_rate = ((curr_p - my_p) / my_p) * 100
                if p_rate > 5 and float(data['RSI'].iloc[-1]) > 65:
                    st.warning("🔥 **스윙 팁:** 수익권+과열! 분할 익절 후 눌림목 재매수 고려")
            st.caption(f"동기화 완료: {datetime.now().strftime('%H:%M:%S')}")
