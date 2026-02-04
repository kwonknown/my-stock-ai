import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. 앱 설정 (타이틀 수정: kwonknown)
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# 2. 지능형 티커 검색 기능
def search_ticker(query):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers).json()
        if res['quotes']: return res['quotes'][0]['symbol']
    except: return None
    return None

# 3. 보조지표 및 세력 평단가(VWAP) 계산
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

# --- 사이드바: 검색 및 즐겨찾기 ---
if 'history' not in st.session_state: st.session_state['history'] = []
st.sidebar.header("🔍 스마트 종목 검색")
search_query = st.sidebar.text_input("종목명(한글/영어) 또는 티커", "팔란티어")
ticker = search_ticker(search_query)

if ticker and search_query not in st.session_state['history']:
    st.session_state['history'].insert(0, search_query)
    st.session_state['history'] = st.session_state['history'][:5]

st.sidebar.write("---")
st.sidebar.subheader("⭐ 최근 본 종목")
for h in st.session_state['history']:
    if st.sidebar.button(f"📍 {h}", key=f"hist_{h}"):
        search_query = h
        ticker = search_ticker(h)

# --- 메인 대시보드 (타이틀 수정: kwonknown) ---
st.title("🛡️ kwonknown AI 투자 전략실 Master")

if ticker:
    try:
        stock_obj = yf.Ticker(ticker)
        data = stock_obj.history(period="1y")
        if not data.empty:
            data = calculate_indicators(data)
            info = stock_obj.info
            curr = data.iloc[-1]
            curr_price = float(curr['Close'])
            vwap_val = float(curr['VWAP'])
            ma20_val = float(curr['MA20'])
            
            # 상단 요약
            st.header(f"{info.get('longName', search_query)} ({ticker})")
            c1, c2, c3, c4 = st.columns(4)
            
            buy_score = 0
            guides = []
            
            # 지표 체크리스트
            if curr_price > vwap_val:
                buy_score += 20
                guides.append("✅ **수급(VWAP):** 세력 평단 위에서 지지받는 중입니다.")
            else:
                guides.append("❌ **수급(VWAP):** 세력 평단 아래입니다. 저항을 주의하세요.")
            
            if curr_price > ma20_val:
                buy_score += 20
                guides.append("✅ **추세:** 20일선 위에 안착하여 심리가 살아있습니다.")
            else:
                guides.append("❌ **추세:** 20일선 아래입니다. 돌파가 필요한 시점입니다.")
            
            rsi_val = float(curr['RSI'])
            if rsi_val < 35: buy_score += 20; guides.append(f"✅ **과열도(RSI:{rsi_val:.1f}):** 바닥권 반등이 임박했습니다.")
            elif rsi_val > 65: guides.append(f"❌ **과열도(RSI:{rsi_val:.1f}):** 고점권입니다. 조심하세요.")
            else: guides.append(f"ℹ️ **과열도(RSI:{rsi_val:.1f}):** 적정 수준입니다.")
            
            if float(curr['MACD']) > float(curr['Signal']): buy_score += 20; guides.append("✅ **에너지:** 상승 에너지가 하락을 압도합니다.")
            else: guides.append("❌ **에너지:** 에너지가 약화되고 있습니다.")
            
            if curr_price < float(curr['BB_Low']): buy_score += 20; guides.append("✅ **가격:** 밴드 하단 이탈로 반등 확률이 높습니다.")
            else: guides.append("ℹ️ **가격:** 박스권 내 안정적인 흐름입니다.")

            c1.metric("🟢 매수 승률", f"{buy_score}%")
            c2.metric("🟠 하락 위험도", f"{100-buy_score}%")
            c3.metric("🎯 세력 평단(VWAP)", f"{vwap_val:.2f}")
            c4.metric("📈 ROE", f"{info.get('returnOnEquity', 0)*100:.1f}%")

            # 차트 및 가이드
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Price'))
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단(VWAP)'))
                fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='orange'), name='20일선'))
                fig.add_annotation(x=data.index[-1], y=curr_price, text=f"현재가:{curr_price:.2f}", showarrow=True)
                fig.update_layout(height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader("📝 애널리스트 상세 가이드")
                for g in guides: st.markdown(g)
                st.write("---")
                if buy_score >= 80: st.success(f"💎 **강력 매수 구간 (승률 {buy_score}%)**")
                elif buy_score <= 20: st.error(f"⚠️ **위험 관리 구간**")
                else: st.info("⚖️ **중립/관망 구간**")
                
                st.write("---")
                st.subheader("📊 기업 체력")
                st.write(f"**부채비율:** {info.get('debtToEquity', 0):.1f}%")
                st.write(f"**시가총액:** {info.get('marketCap', 0)/1e12:.2f}T")

    except Exception as e:
        st.error(f"분석 중 오류가 발생했습니다: {e}")
