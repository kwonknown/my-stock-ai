import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. 앱 설정
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# 2. 한글 검색 및 티커 자동 변환 엔진 (강화 버전)
def get_ticker_pro(query):
    mapping = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS",
        "현대건설": "000720.KS", "삼표시멘트": "023410.KS", "팔란티어": "PLTR",
        "테슬라": "TSLA", "엔비디아": "NVDA", "아이온큐": "IONQ", "애플": "AAPL"
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

# 3. 보조지표 계산
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

# 4. 종목 발굴 로직 (80% 이상 찾기)
def scan_high_probability():
    candidates = ["PLTR", "TSLA", "NVDA", "AAPL", "005930.KS", "000660.KS", "000720.KS", "IONQ", "AMD", "MSFT"]
    high_prob_list = []
    
    for t in candidates:
        try:
            d = yf.Ticker(t).history(period="1mo")
            if len(d) < 20: continue
            d = calculate_indicators(d)
            c = d.iloc[-1]
            score = 0
            if float(c['Close']) > float(c['VWAP']): score += 20
            if float(c['Close']) > float(c['MA20']): score += 20
            if float(c['RSI']) < 40: score += 20
            if float(c['MACD']) > float(c['Signal']): score += 20
            if float(c['Close']) < float(c['BB_High']): score += 20 # 과열 아님
            
            if score >= 80:
                high_prob_list.append({"티커": t, "승률": score})
        except: continue
    return high_prob_list

# --- 사이드바 ---
st.sidebar.header("🔍 분석 설정")
search_query = st.sidebar.text_input("종목명 또는 티커", "삼성전자")
my_avg_price = st.sidebar.number_input("나의 매수 평단가 (0이면 미적용)", value=0.0)
ticker = get_ticker_pro(search_query)

if st.sidebar.button("💎 승률 80% 이상 종목 발굴"):
    with st.sidebar:
        with st.spinner('시장 탐색 중...'):
            results = scan_high_probability()
            if results:
                for r in results: st.success(f"📍 {r['티커']} (승률: {r['승률']}%)")
            else: st.warning("현재 승률 80% 이상인 종목이 없습니다.")

# --- 메인 분석 ---
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
            
            # 상단 메트릭 구성 (현재가 추가)
            st.header(f"{info.get('longName', search_query)} ({ticker})")
            c1, c2, c3, c4 = st.columns(4)
            
            # 승률 계산
            buy_score = 0
            guides = []
            if curr_price > vwap_val: buy_score += 20; guides.append("✅ **수급:** 세력 평단 지지 중")
            if curr_price > float(curr['MA20']): buy_score += 20; guides.append("✅ **추세:** 20일선 위 안착")
            if float(curr['RSI']) < 40: buy_score += 20; guides.append("✅ **심리:** 저평가/과매도 구간")
            if float(curr['MACD']) > float(curr['Signal']): buy_score += 20; guides.append("✅ **에너지:** 골든크로스 발생")
            if curr_price < float(curr['BB_High']): buy_score += 20; guides.append("✅ **위치:** 추가 상승 여력 충분")

            c1.metric("📈 현재가", f"{curr_price:,.2f}")
            c2.metric("🟢 매수 승률", f"{buy_score}%")
            if my_avg_price > 0:
                p_rate = ((curr_price - my_avg_price) / my_avg_price) * 100
                c3.metric("💰 나의 수익률", f"{p_rate:+.2f}%")
            else:
                c3.metric("🎯 세력 평단", f"{vwap_val:,.2f}")
            c4.metric("📊 ROE", f"{info.get('returnOnEquity', 0)*100:.1f}%")

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
                st.subheader("📝 상세 분석 가이드")
                for g in guides: st.write(g)
                if buy_score >= 80: st.success("💎 **강력 추천: 승률 80% 이상의 황금 구간!**")
                elif buy_score >= 60: st.info("🔭 관망하며 분할 매수 고려")
                else: st.error("⚠️ 위험 관리 및 관망 구간")

    except Exception as e:
        st.error(f"데이터를 불러올 수 없습니다. 티커를 확인해 주세요: {e}")
