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
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_High'] = df['MA20'] + (df['BB_std'] * 2)
    df['BB_Low'] = df['MA20'] - (df['BB_std'] * 2)
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

# 4. 프리미엄 종목 발굴 로직
def scan_premium_stocks():
    watchlist = ["AAPL", "NVDA", "TSLA", "PLTR", "005930.KS", "000660.KS", "000720.KS", "AMD", "IONQ"]
    results = []
    for t in watchlist:
        try:
            stock = yf.Ticker(t)
            d = stock.history(period="2mo")
            if len(d) < 20: continue
            d = calculate_indicators(d)
            c = d.iloc[-1]
            info = stock.info
            score = 0
            if float(c['Close']) > float(c['VWAP']): score += 20
            if float(c['Close']) > float(c['MA20']): score += 20
            if 30 < float(c['RSI']) < 60: score += 20
            if float(c['MACD']) > float(c['Signal']): score += 20
            if float(c['Close']) < float(c['BB_High']): score += 20
            if score >= 80:
                results.append({"티커": t, "승률": score, "ROE": info.get('returnOnEquity', 0)*100, "부채": info.get('debtToEquity', 0)})
        except: continue
    return results

# --- 사이드바 ---
st.sidebar.header("🔍 분석 & 발굴")
search_query = st.sidebar.text_input("종목명 입력", "삼성전자")
my_avg_price = st.sidebar.number_input("나의 매수 평단가", value=0.0)
ticker = get_ticker_pro(search_query)

if st.sidebar.button("💎 우량주 중심 80% 승목 발굴"):
    with st.sidebar:
        premium_list = scan_premium_stocks()
        if premium_list:
            for p in premium_list:
                st.write(f"✅ **{p['티커']}** (승률:{p['승률']}%)")
                st.caption(f"ROE: {p['ROE']:.1f}% / 부채: {p['부채']:.1f}%")

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
            ma20_val = float(curr['MA20'])
            rsi_val = float(curr['RSI'])
            
            # 상단 메트릭
            st.header(f"{info.get('longName', search_query)} ({ticker})")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📈 현재가", f"{curr_price:,.2f}")
            
            # 5대 지표 및 승률 계산
            buy_score = 0
            guides = []
            if curr_price > vwap_val:
                buy_score += 20
                guides.append("✅ **수급(VWAP):** 세력 평단 위에서 지지받는 중입니다.")
            else:
                guides.append("❌ **수급(VWAP):** 세력 평단 아래입니다. 저항을 주의하세요.")
            
            if curr_price > ma20_val:
                buy_score += 20
                guides.append("✅ **추세:** 20일선 위에 안착하여 심리가 살아있습니다.")
            else:
                guides.append("❌ **추세:** 20일선 아래입니다. 돌파가 필요합니다.")
            
            if rsi_val < 35:
                buy_score += 20
                guides.append(f"✅ **과열도(RSI:{rsi_val:.1f}):** 바닥권 반등이 임박했습니다.")
            elif rsi_val > 65:
                guides.append(f"❌ **과열도(RSI:{rsi_val:.1f}):** 고점권입니다. 조심하세요.")
            else:
                guides.append(f"ℹ️ **과열도(RSI:{rsi_val:.1f}):** 적정 수준입니다.")
            
            if float(curr['MACD']) > float(curr['Signal']):
                buy_score += 20
                guides.append("✅ **에너지:** 상승 에너지가 하락을 압도합니다.")
            else:
                guides.append("❌ **에너지:** 에너지가 약화되고 있습니다.")
            
            if curr_price < float(curr['BB_Low']):
                buy_score += 20
                guides.append("✅ **가격:** 밴드 하단 이탈로 반등 확률이 높습니다.")
            else:
                guides.append("ℹ️ **가격:** 박스권 내 안정적인 흐름입니다.")

            m2.metric("🟢 매수 승률", f"{buy_score}%")
            if my_avg_price > 0:
                p_rate = ((curr_price - my_avg_price) / my_avg_price) * 100
                m3.metric("💰 나의 수익률", f"{p_rate:+.2f}%")
            else:
                m3.metric("🎯 세력 평단", f"{vwap_val:,.2f}")
            
            roe_val = info.get('returnOnEquity', 0) * 100
            m4.metric("📊 ROE", f"{roe_val:.1f}%")

            # 차트 및 우측 상세 분석
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
                st.subheader("📝 애널리스트 상세 분석")
                for g in guides: st.markdown(g)
                st.write("---")
                st.subheader("💡 kwonknown 스윙 가이드")
                if my_avg_price > 0:
                    if p_rate > 5 and rsi_val > 65:
                        st.warning("🔥 **익절 타이밍:** 수익권이며 지표가 과열되었습니다.")
                    elif curr_price <= vwap_val * 1.02:
                        st.success("💎 **재매수 구간:** 세력 평단 근처입니다. 수량 확대를 고려하세요.")
                
                st.write("---")
                if buy_score >= 80: st.success(f"💎 **강력 매수 (승률 {buy_score}%)**")
                elif buy_score <= 20: st.error(f"⚠️ **위험 관리 (관망)**")
                else: st.info("⚖️ **중립/보류 구간**")

                st.write("---")
                st.subheader("📊 기업 재무 현황")
                st.write(f"**부채비율:** {info.get('debtToEquity', 0):.1f}%")
                st.write(f"**시가총액:** {info.get('marketCap', 0)/1e12:.2f}T")
                st.write(f"**배당률:** {info.get('dividendYield', 0)*100:.2f}%")

    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
