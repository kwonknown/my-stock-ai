import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# 1. 앱 설정 및 세션 상태 관리
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

if 'selected_stock' not in st.session_state:
    st.session_state['selected_stock'] = "삼성전자"

@st.cache_data(ttl=600)
def get_stock_data(ticker):
    return yf.Ticker(ticker).history(period="1y")

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
    df['BB_Low'] = df['MA20'] - (df['BB_std'] * 2)
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

# 4. 보수적 추세 확증 승률 로직
def calculate_conservative_score(curr, info):
    curr_price = float(curr['Close'])
    vwap_val = float(curr['VWAP'])
    ma20_val = float(curr['MA20'])
    rsi_val = float(curr['RSI'])
    if curr_price < vwap_val or curr_price < ma20_val: return 30
    if curr_price > vwap_val * 1.15: return 60
    score = 70
    if curr_price > ma20_val > vwap_val: score += 10
    if float(curr['MACD']) > float(curr['Signal']): score += 5
    if 40 < rsi_val < 60: score += 15
    elif rsi_val >= 65: score -= 10
    return min(max(score, 0), 100)

# --- 사이드바 ---
st.sidebar.header("🔍 마켓 스캐너")
input_query = st.sidebar.text_input("종목명 입력", value=st.session_state['selected_stock'])
my_avg_price = st.sidebar.number_input("나의 매수 평단가", value=0.0)

if st.sidebar.button("💎 보수적 우량주 전수 조사"):
    watchlist = ["AAPL", "NVDA", "TSLA", "PLTR", "005930.KS", "000660.KS", "000720.KS", "214450.KQ", "IONQ", "AMD"]
    with st.sidebar:
        st.write("---")
        for t in watchlist:
            try:
                s = yf.Ticker(t)
                d = calculate_indicators(s.history(period="2mo"))
                sc = calculate_conservative_score(d.iloc[-1], s.info)
                if sc >= 80:
                    if st.button(f"🚀 {t} (승률:{sc}%)", key=f"btn_{t}"):
                        st.session_state['selected_stock'] = t
                        st.rerun()
            except: continue

# --- 메인 분석 화면 ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")
ticker = get_ticker_pro(st.session_state['selected_stock'] if input_query == st.session_state['selected_stock'] else input_query)

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
            ma20_val = float(curr['MA20'])
            rsi_val = float(curr['RSI'])
            roe_val = info.get('returnOnEquity', 0) * 100
            
            buy_score = calculate_conservative_score(curr, info)
            
            # 상단 메트릭
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

            # 지표 체크리스트 생성
            guides = []
            if curr_price > vwap_val: guides.append("✅ **수급(VWAP):** 세력 평단 위 지지 중")
            else: guides.append("❌ **수급(VWAP):** 세력 평단 아래 저항 주의")
            if curr_price > ma20_val: guides.append("✅ **추세:** 20일선 위 안착 (심리 양호)")
            else: guides.append("❌ **추세:** 20일선 아래 (상향 돌파 필요)")
            if 30 < rsi_val < 65: guides.append(f"✅ **과열도(RSI:{rsi_val:.1f}):** 적정 심리 구간")
            else: guides.append(f"⚠️ **과열도(RSI:{rsi_val:.1f}):** 과열/침체 경계")
            if float(curr['MACD']) > float(curr['Signal']): guides.append("✅ **에너지:** 상승 에너지 우위")
            else: guides.append("❌ **에너지:** 하락/약화 에너지 우위")
            if curr_price < float(curr['BB_High']): guides.append("✅ **가격:** 추가 상승 여력 충분")
            else: guides.append("⚠️ **가격:** 밴드 상단 도달 (조정 주의)")

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
                st.subheader("🔍 지속 가능성 진단")
                if roe_val > 10: st.success(f"💎 **이익 지속성 상급:** ROE {roe_val:.1f}% 우량주")
                else: st.warning(f"⚠️ **이익 지속성 체크:** 수익성 개선 필요")

                st.write("---")
                st.subheader("📝 상세 지표 분석")
                for g in guides: st.markdown(g)

                st.write("---")
                st.subheader("💡 kwonknown 투자 가이드")
                if buy_score >= 80: st.success(f"🚀 **강력 매수 진입 구간 (승률 {buy_score}%)**")
                elif buy_score >= 60: st.info("⚖️ **중립/관망: 추세는 좋으나 고점 경계**")
                else: st.error("⏳ **위험 관리: 하락 추세 또는 지지선 미달**")

                if my_avg_price > 0:
                    if p_rate > 5 and rsi_val > 65: st.warning("🔥 **스윙 팁:** 수익권+과열! 익절 후 눌림목 재매수 권장")
                    elif curr_price <= vwap_val * 1.02: st.success("💎 **스윙 팁:** 세력 평단 지지 중, 수량 확대 적기")

                st.write("---")
                st.subheader("📊 기업 재무 상세")
                st.write(f"**부채비율:** {info.get('debtToEquity', 0):.1f}%")
                st.write(f"**시가총액:** {info.get('marketCap', 0)/1e12:.2f}T")
                st.caption(f"최종 업데이트: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        st.error(f"분석 오류: {e}")
