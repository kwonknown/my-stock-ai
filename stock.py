import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 세션 상태
st.set_page_config(page_title="kwonknown AI Master", layout="wide")
if 'selected_stock' not in st.session_state: st.session_state['selected_stock'] = "삼성전자"

@st.cache_data(ttl=600)
def get_stock_data(ticker): return yf.Ticker(ticker).history(period="1y")

# 2. 통합 검색 엔진
def get_ticker_pro(query):
    mapping = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS",
        "현대건설": "000720.KS", "파마리서치": "214450.KQ", "리쥬란": "214450.KQ",
        "팔란티어": "PLTR", "테슬라": "TSLA", "엔비디아": "NVDA", "아이온큐": "IONQ"
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
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_High'] = df['MA20'] + (df['BB_std'] * 2)
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

# 4. 스마트 밸런스 승률 로직 (수익성+안정성)
def calculate_balanced_score(curr, info):
    cp = float(curr['Close']); vwap = float(curr['VWAP']); ma = float(curr['MA20'])
    rsi = float(curr['RSI']); roe = info.get('returnOnEquity', 0) * 100
    
    if cp < vwap * 0.98 and cp < ma * 0.98: return 35 # 확실한 하락세만 컷오프
    
    score = 65 # 기본 점수 상향
    if cp > vwap: score += 10
    if cp > ma: score += 10
    if float(curr['MACD']) > float(curr['Signal']): score += 5
    if 35 < rsi < 65: score += 10 # 적정 구간 가점
    if roe > 15: score += 5 # 우량 재무 가점
    if cp > vwap * 1.2: score -= 15 # 과한 급등 경계
    
    return min(max(score, 0), 100)

# --- 사이드바: 섹터별 확장 스캐너 ---
st.sidebar.header("📡 글로벌 섹터 스캐너")
input_q = st.sidebar.text_input("종목명 입력", value=st.session_state['selected_stock'])
my_avg = st.sidebar.number_input("나의 매수 평단가", value=0.0)

sectors = {
    "AI/반도체": ["NVDA", "AMD", "AVGO", "005930.KS", "000660.KS", "ASML", "TSM"],
    "빅테크/SaaS": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "PLTR", "SNOW"],
    "미래차/에너지": ["TSLA", "005380.KS", "000270.KS", "RIVN", "ENPH"],
    "바이오/헬스": ["214450.KQ", "LLY", "NVO", "068270.KS", "PFE"],
    "한국 우량주": ["000720.KS", "035420.KS", "035720.KS", "005490.KS", "105560.KS"]
}

if st.sidebar.button("💎 글로벌 전 섹터 전수 조사"):
    with st.sidebar:
        for sec, tickers in sectors.items():
            st.markdown(f"**[{sec}]**")
            for t in tickers:
                try:
                    s = yf.Ticker(t)
                    d = calculate_indicators(s.history(period="2mo")).iloc[-1]
                    sc = calculate_balanced_score(d, s.info)
                    if sc >= 75: # 기준을 75로 살짝 낮추어 기회 포착
                        if st.button(f"🚀 {t} ({sc}%)", key=f"btn_{t}"):
                            st.session_state['selected_stock'] = t
                            st.rerun()
                except: continue

# --- 메인 대시보드 (지표 완벽 복구) ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")
ticker = get_ticker_pro(st.session_state['selected_stock'] if input_q == st.session_state['selected_stock'] else input_q)

if ticker:
    try:
        stock_obj = yf.Ticker(ticker)
        data = get_stock_data(ticker)
        if not data.empty:
            data = calculate_indicators(data)
            info = stock_obj.info
            curr = data.iloc[-1]
            cp = float(curr['Close']); vwap = float(curr['VWAP']); ma = float(curr['MA20'])
            rsi = float(curr['RSI']); roe = info.get('returnOnEquity', 0) * 100
            
            sc = calculate_balanced_score(curr, info)
            st.header(f"{info.get('longName', ticker)} ({ticker})")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📈 현재가", f"{cp:,.2f}")
            c2.metric("🟢 스마트 승률", f"{sc}%")
            if my_avg > 0:
                p_r = ((cp - my_avg) / my_avg) * 100
                c3.metric("💰 나의 수익률", f"{p_r:+.2f}%")
            else: c3.metric("🎯 세력 평단", f"{vwap:,.2f}")
            c4.metric("📊 ROE", f"{roe:.1f}%")

            guides = []
            if cp > vwap: guides.append("✅ **수급:** 세력 평단 위 지지 중")
            else: guides.append("❌ **수급:** 세력 평단 아래 저항 주의")
            if cp > ma: guides.append("✅ **추세:** 20일선 위 안착")
            else: guides.append("❌ **추세:** 20일선 아래 돌파 필요")
            if 35 < rsi < 65: guides.append(f"✅ **심리:** 적정 구간 ({rsi:.1f})")
            else: guides.append(f"⚠️ **심리:** 과열/침체 경계 ({rsi:.1f})")

            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='주가')])
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
                fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='orange'), name='20일선'))
                if my_avg > 0: fig.add_hline(y=my_avg, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader("🔍 지속 가능성 진단")
                if roe > 10: st.success(f"💎 **이익 지속성 우량:** ROE {roe:.1f}%")
                else: st.warning(f"⚠️ **성장성 체크 필요**")
                st.write("---")
                st.subheader("📝 상세 지표 분석")
                for g in guides: st.markdown(g)
                st.write("---")
                st.subheader("💡 kwonknown 가이드")
                if sc >= 80: st.success(f"🚀 **강력 진입 구간!**")
                elif sc >= 60: st.info(f"⚖️ **관망 및 분할 대응**")
                else: st.error(f"⏳ **위험 관리 시점**")
                
                st.write(f"**부채비율:** {info.get('debtToEquity', 0):.1f}%")
                st.caption(f"업데이트: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e: st.error(f"분석 오류: {e}")
