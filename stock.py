import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 스마트 캐싱 (API 보호 모드)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# 'history'와 'search' 상태가 없으면 미리 만들어줍니다.
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'search' not in st.session_state:
    st.session_state['search'] = ""

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

# --- 사이드바: 섹터별 퀵 메뉴 & 히스토리 ---
with st.sidebar:
    st.header("🚀 섹터별 주요 종목")

    # 1. 반도체 & 빅테크
    with st.expander("💻 반도체 & 빅테크", expanded=True):
        c1, c2 = st.columns(2)
        if c1.button("삼성전자"): st.session_state['search'] = "005930.KS"
        if c1.button("SK하이닉스"): st.session_state['search'] = "000660.KS"
        if c2.button("MSFT"): st.session_state['search'] = "MSFT"
        if c2.button("엔비디아"): st.session_state['search'] = "NVDA"

    # 2. 바이오 & 뷰티
    with st.expander("🧪 바이오 & 💄 뷰티", expanded=False):
        c1, c2 = st.columns(2)
        if c1.button("파마리서치"): st.session_state['search'] = "214450.KQ"
        if c1.button("유한양행"): st.session_state['search'] = "000100.KS"
        if c2.button("에이피알"): st.session_state['search'] = "277470.KS"
        if c2.button("아모레퍼시픽"): st.session_state['search'] = "090430.KS"

    # 3. 방산 & 광산(자원)
    with st.expander("🛡️ 방산 & ⛏️ 광산", expanded=False):
        c1, c2 = st.columns(2)
        if c1.button("한화에어로"): st.session_state['search'] = "012450.KS"
        if c1.button("현대로템"): st.session_state['search'] = "064350.KS"
        if c2.button("포스코홀딩스"): st.session_state['search'] = "005490.KS"
        if c2.button("리튬아메리카"): st.session_state['search'] = "LAC"

    # 4. 로봇 & 기타
    with st.expander("🤖 로봇 & 💡 성장주", expanded=False):
        c1, c2 = st.columns(2)
        if c1.button("휴림로봇"): st.session_state['search'] = "090710.KQ"
        if c1.button("레인보우로보"): st.session_state['search'] = "277810.KQ"
        if c2.button("팔란티어"): st.session_state['search'] = "PLTR"
        if c2.button("테슬라"): st.session_state['search'] = "TSLA"

    st.write("---")
    
    # 최근 검색 히스토리 유지
    if st.session_state['history']:
        st.subheader("🕒 히스토리 (최근 5)")
        for h_item in st.session_state['history']:
            if st.button(f"📜 {h_item}", key=f"sidebar_hist_{h_item}"):
                st.session_state['search'] = h_item
                
        # --- 승률 80% 이상 종목 발굴 섹션 추가 ---
    st.write("---")
    st.subheader("💎 실시간 종목 발굴")
    
    if st.button("🚀 승률 80%↑ 종목 스캔"):
        # 스캔 대상: 섹터별 주요 종목 리스트 통합
        scan_list = [
            "005930.KS", "000660.KS", "MSFT", "NVDA", "PLTR", "TSLA", 
            "214450.KQ", "000100.KS", "277470.KS", "012450.KS", 
            "064350.KS", "005490.KS", "090710.KQ", "IONQ", "AMD"
        ]
        
        with st.spinner('안정적 우상향 종목 찾는 중...'):
            high_score_stocks = []
            for t in scan_list:
                try:
                    # 데이터 호출 및 지표 계산 (캐시 활용)
                    d = calculate_indicators(yf.Ticker(t).history(period="2mo"))
                    if d.empty: continue
                    
                    # 엄격한 승률 로직 적용
                    s_info = yf.Ticker(t).info
                    score = calculate_strict_score(d.iloc[-1], s_info)
                    
                    if score >= 80:
                        high_score_stocks.append({"ticker": t, "score": score})
                except:
                    continue
            
            # 결과 출력
            if high_score_stocks:
                st.success(f"{len(high_score_stocks)}개의 보석 발견!")
                for s in high_score_stocks:
                    if st.button(f"🔥 {s['ticker']} ({s['score']}%)", key=f"scan_{s['ticker']}"):
                        st.session_state['search'] = s['ticker']
            else:
                st.warning("현재 80% 이상인 종목이 없습니다.")

    st.write("---")
    
    search_q = st.text_input("종목명/티커 직접 입력", value=st.session_state.get('search', ""))
    my_price = st.number_input("나의 평단가", value=0.0)
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

            # 메인 분석 영역 (차트 + 가이드)
            col_left, col_right = st.columns([2, 1])
            with col_left:
                fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
                if my_price > 0: 
                    fig.add_hline(y=my_price, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col_right:
                st.subheader("🔍 지속 가능성")
                if roe > 10: st.success(f"💎 **이익 지속성 상급:** ROE {roe:.1f}%")
                else: st.info(f"⚖️ **이익 지속성 보통:** 재무 건전성 확인 필요")
                
                st.subheader("📝 상세 지표 분석")
                for g in guides: st.markdown(g)
                
                st.write("---")
                st.subheader("💡 투자 판단")
                if buy_score >= 80: st.success("🚀 **강력 매수 구간**")
                elif buy_score <= 40: st.error("⚠️ **관망/위험 관리 시점**")
                else: st.info("⚖️ **중립 구간**")
            
            st.success(f"✅ 분석 완료 ({datetime.now().strftime('%H:%M:%S')})")
        else:
            st.error("앗! 데이터 수신에 실패했습니다. 1분만 쉬었다가 다시 눌러주세요.")
    else:
        st.error("종목 티커를 찾을 수 없습니다. 정확한 이름을 입력해주세요.")
else:
    st.info("왼쪽 검색창에 종목을 넣고 [📊 분석 시작] 버튼을 눌러주세요! 😊")
