import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 기본 설정 및 캐시 제어 (데이터 지연 최소화)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# 데이터 갱신을 위한 캐시 설정 (10분마다 강제 업데이트)
@st.cache_data(ttl=600)
def get_stock_data(ticker):
    data = yf.Ticker(ticker).history(period="1y")
    return data

# 2. 지능형 티커 검색 엔진 (코스피/코스닥/미장 통합)
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
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers).json()
        if res['quotes']: return res['quotes'][0]['symbol']
    except: return None
    return query

# 3. 보조지표 계산 함수
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

# --- 사이드바 및 글로벌 스캔 ---
st.sidebar.header("🔍 분석 및 발굴")
search_query = st.sidebar.text_input("종목명 입력", "삼성전자")
my_avg_price = st.sidebar.number_input("나의 매수 평단가", value=0.0)
ticker = get_ticker_pro(search_query)

if st.sidebar.button("💎 글로벌 우량주 80% 승목 스캔"):
    watchlist = ["AAPL", "NVDA", "TSLA", "PLTR", "005930.KS", "000660.KS", "000720.KS", "214450.KQ", "IONQ"]
    with st.sidebar:
        with st.spinner('실시간 분석 중...'):
            for t in watchlist:
                try:
                    d = calculate_indicators(yf.Ticker(t).history(period="2mo"))
                    c = d.iloc[-1]
                    score = 0
                    if float(c['Close']) > float(c['VWAP']): score += 20
                    if float(c['Close']) > float(c['MA20']): score += 20
                    if 30 < float(c['RSI']) < 60: score += 20
                    if float(c['MACD']) > float(c['Signal']): score += 20
                    if float(c['Close']) < float(c['BB_High']): score += 20
                    if score >= 80:
                        st.write(f"✅ **{t}** (승률:{score}%)")
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
            
            # 상단 메트릭
            st.header(f"{info.get('longName', search_query)} ({ticker})")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 실시간급 현재가", f"{curr_price:,.2f}")
            
            buy_score = 0
            guides = []
            # 5대 지표 체크리스트 로직 (생략 없이 포함)
            if curr_price > vwap_val: buy_score += 20; guides.append("✅ **수급(VWAP):** 세력 평단 위 지지 중")
            else: guides.append("❌ **수급(VWAP):** 세력 평단 아래 저항")
            if curr_price > float(curr['MA20']): buy_score += 20; guides.append("✅ **추세:** 20일선 위 안착")
            else: guides.append("❌ **추세:** 20일선 아래")
            if 30 < float(curr['RSI']) < 65: buy_score += 20; guides.append("✅ **심리:** 과열 없는 적정 구간")
            else: guides.append("⚠️ **심리:** 과열 또는 침체 주의")
            if float(curr['MACD']) > float(curr['Signal']): buy_score += 20; guides.append("✅ **에너지:** 상승세 우위")
            else: guides.append("❌ **에너지:** 하락세 우위")
            if curr_price < float(curr['BB_High']): buy_score += 20; guides.append("✅ **가격:** 추가 상승 여력 있음")
            else: guides.append("⚠️ **가격:** 밴드 상단 도달")

            m2.metric("🟢 매수 승률", f"{buy_score}%")
            if my_avg_price > 0:
                p_rate = ((curr_price - my_avg_price) / my_avg_price) * 100
                m3.metric("💰 나의 수익률", f"{p_rate:+.2f}%")
            else:
                m3.metric("🎯 세력 평단", f"{vwap_val:,.2f}")
            m4.metric("📊 ROE", f"{roe_val:.1f}%")

            # 차트 및 우측 분석창
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='주가')])
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
                if my_avg_price > 0:
                    fig.add_hline(y=my_avg_price, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader("🔍 지속 가능성 및 지표")
                if roe_val > 10: st.success(f"💎 **이익 지속성 상급:** ROE {roe_val:.1f}% 우량주")
                else: st.warning(f"⚠️ **수익성 체크:** ROE가 낮아 장기 투자 주의")
                
                for g in guides: st.write(g)
                st.write("---")
                st.subheader("💡 투자 판단")
                if buy_score >= 80: st.success(f"🚀 **강력 매수 (승률 {buy_score}%)**")
                elif buy_score <= 20: st.error(f"⏳ **위험 관리 (관망)**")
                else: st.info("⚖️ **중립/보류**")
                
                if my_avg_price > 0:
                    if p_rate > 5 and float(curr['RSI']) > 65: st.warning("🔥 **스윙:** 일부 익절 후 재매수 대기!")
                    elif curr_price <= vwap_val * 1.02: st.success("💎 **스윙:** 세력 평단 부근, 수량 확대 적기")

                st.caption(f"최종 업데이트: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
