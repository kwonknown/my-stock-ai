import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. 앱 설정
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# 2. 지능형 티커 검색
def get_ticker_pro(query):
    mapping = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS",
        "현대건설": "000720.KS", "팔란티어": "PLTR", "테슬라": "TSLA", "엔비디아": "NVDA"
    }
    if query in mapping: return mapping[query]
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers).json()
        if res['quotes']: return res['quotes'][0]['symbol']
    except: return None
    return query

# 3. 지표 계산 함수
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
    df['BB_High'] = df['MA20'] + (df['Close'].rolling(window=20).std() * 2)
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

# 4. 프리미엄 종목 발굴 로직 (기술적 승률 + 재무 건전성)
def scan_premium_stocks():
    global_watchlist = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AVGO", "COST", "NFLX",
        "PLTR", "IONQ", "AMD", "005930.KS", "000660.KS", "005380.KS", "000720.KS", "035420.KS"
    ]
    
    results = []
    for t in global_watchlist:
        try:
            stock = yf.Ticker(t)
            d = stock.history(period="2mo")
            if len(d) < 20: continue
            d = calculate_indicators(d)
            c = d.iloc[-1]
            info = stock.info
            
            # 기술 점수 (80점 이상 목표)
            score = 0
            if float(c['Close']) > float(c['VWAP']): score += 20
            if float(c['Close']) > float(c['MA20']): score += 20
            if 30 < float(c['RSI']) < 60: score += 20  # 너무 과열되지 않은 상승 초입
            if float(c['MACD']) > float(c['Signal']): score += 20
            if float(c['Close']) < float(c['BB_High']): score += 20
            
            # 재무 필터 (ROE 10% 이상, 부채 150% 미만 우선)
            roe = info.get('returnOnEquity', 0) * 100
            debt = info.get('debtToEquity', 0)
            
            if score >= 80:
                results.append({"티커": t, "승률": score, "ROE": roe, "부채": debt})
        except: continue
    return results

# --- 사이드바 및 레이아웃 ---
st.sidebar.header("🔍 분석 & 발굴")
search_query = st.sidebar.text_input("종목명 입력", "삼성전자")
my_avg_price = st.sidebar.number_input("나의 매수 평단가", value=0.0)
ticker = get_ticker_pro(search_query)

if st.sidebar.button("💎 우량주 중심 80% 승목 발굴"):
    with st.sidebar:
        with st.spinner('재무 및 차트 전수 조사 중...'):
            premium_list = scan_premium_stocks()
            if premium_list:
                for p in premium_list:
                    color = "🟢" if p['ROE'] > 10 and p['부채'] < 100 else "🟡"
                    st.write(f"{color} **{p['티커']}** (승률:{p['승률']}%)")
                    st.caption(f"ROE: {p['ROE']:.1f}% / 부채: {p['부채']:.1f}%")
            else: st.warning("조건에 맞는 우량주가 없습니다.")

# --- 메인 분석 화면 ---
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
            
            # 상단 메트릭
            st.header(f"{info.get('longName', search_query)} ({ticker})")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 현재가", f"{curr_price:,.2f}")
            
            buy_score = 0
            if curr_price > vwap_val: buy_score += 20
            if curr_price > float(curr['MA20']): buy_score += 20
            if 30 < float(curr['RSI']) < 60: buy_score += 20
            if float(curr['MACD']) > float(curr['Signal']): buy_score += 20
            if curr_price < float(curr['BB_High']): buy_score += 20

            m2.metric("🟢 매수 승률", f"{buy_score}%")
            
            if my_avg_price > 0:
                p_rate = ((curr_price - my_avg_price) / my_avg_price) * 100
                m3.metric("💰 나의 수익률", f"{p_rate:+.2f}%")
            else:
                m3.metric("🎯 세력 평단", f"{vwap_val:,.2f}")
            
            roe_val = info.get('returnOnEquity', 0) * 100
            m4.metric("📊 ROE", f"{roe_val:.1f}%")

            # 차트 및 가이드
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='주가')])
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단'))
                if my_avg_price > 0:
                    fig.add_hline(y=my_avg_price, line_dash="solid", line_color="green", annotation_text="내 평단")
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader("📝 지속 가능성 진단")
                if roe_val > 10: st.success(f"✅ **이익 지속성:** ROE가 {roe_val:.1f}%로 우량합니다.")
                else: st.warning(f"⚠️ **수익성 저하:** ROE가 낮아 장기 투자에 주의가 필요합니다.")
                
                st.write("---")
                if my_avg_price > 0:
                    if p_rate > 5 and float(curr['RSI']) > 65:
                        st.warning("🔥 **스윙 타이밍:** 수익권이며 지표가 과열되었습니다. 익절 후 재매수 대기!")
                    elif curr_price <= vwap_val * 1.02:
                        st.success("💎 **수량 확대:** 세력 평단 근처입니다. 지지 확인 후 추가 매수 가능!")

    except Exception as e:
        st.error(f"데이터 분석 오류: {e}")
