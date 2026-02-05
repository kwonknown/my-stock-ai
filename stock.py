import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. 앱 기본 설정
st.set_page_config(page_title="kwonknown AI Master", layout="wide")

# 2. 실시간 티커 검색 엔진
def search_ticker(query):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers).json()
        if res['quotes']: return res['quotes'][0]['symbol']
    except: return None
    return None

# 3. 보조지표 및 VWAP 계산
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

# --- 사이드바: 검색 및 평단가 입력 ---
st.sidebar.header("🔍 분석 설정")
search_query = st.sidebar.text_input("종목명 또는 티커", "삼성전자")
my_avg_price = st.sidebar.number_input("나의 매수 평단가 (0이면 미적용)", value=0.0)

ticker = search_ticker(search_query)

# 즐겨찾기 로직
if 'history' not in st.session_state: st.session_state['history'] = []
if ticker and search_query not in st.session_state['history']:
    st.session_state['history'].insert(0, search_query)
    st.session_state['history'] = st.session_state['history'][:5]

st.sidebar.write("---")
st.sidebar.subheader("⭐ 최근 본 종목")
for h in st.session_state['history']:
    if st.sidebar.button(f"📍 {h}", key=f"hist_{h}"):
        search_query = h
        ticker = search_ticker(h)

# --- 메인 대시보드 ---
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
            
            # 상단 핵심 지표
            st.header(f"{info.get('longName', search_query)} ({ticker})")
            c1, c2, c3, c4 = st.columns(4)
            
            buy_score = 0
            guides = []
            
            # 1. 수급 (VWAP)
            if curr_price > vwap_val:
                buy_score += 20
                guides.append("✅ **수급(VWAP):** 세력 평단 위에서 지지받는 중입니다.")
            else:
                guides.append("❌ **수급(VWAP):** 세력 평단 아래입니다. 저항을 주의하세요.")
            
            # 2. 추세 (MA20)
            if curr_price > ma20_val:
                buy_score += 20
                guides.append("✅ **추세:** 20일선 위에 안착하여 심리가 살아있습니다.")
            else:
                guides.append("❌ **추세:** 20일선 아래입니다. 돌파가 필요한 시점입니다.")
            
            # 3. 과열도 (RSI)
            if rsi_val < 35:
                buy_score += 20
                guides.append(f"✅ **과열도(RSI:{rsi_val:.1f}):** 바닥권 반등이 임박했습니다.")
            elif rsi_val > 65:
                guides.append(f"❌ **과열도(RSI:{rsi_val:.1f}):** 고점권입니다. 조심하세요.")
            else:
                guides.append(f"ℹ️ **과열도(RSI:{rsi_val:.1f}):** 적정 수준입니다.")
            
            # 4. 에너지 (MACD)
            if float(curr['MACD']) > float(curr['Signal']):
                buy_score += 20
                guides.append("✅ **에너지:** 상승 에너지가 하락을 압도합니다.")
            else:
                guides.append("❌ **에너지:** 에너지가 약화되고 있습니다.")
            
            # 5. 가격 (Bollinger Bands)
            if curr_price < float(curr['BB_Low']):
                buy_score += 20
                guides.append("✅ **가격:** 밴드 하단 이탈로 반등 확률이 높습니다.")
            else:
                guides.append("ℹ️ **가격:** 박스권 내 안정적인 흐름입니다.")

            # 지표 메트릭 표시
            if my_avg_price > 0:
                profit_rate = ((curr_price - my_avg_price) / my_avg_price) * 100
                c1.metric("🟢 나의 수익률", f"{profit_rate:+.2f}%")
            else:
                c1.metric("🟢 매수 승률", f"{buy_score}%")
            
            c2.metric("🟠 하락 위험도", f"{100-buy_score}%")
            c3.metric("🎯 세력 평단(VWAP)", f"{vwap_val:,.2f}")
            c4.metric("📈 ROE", f"{info.get('returnOnEquity', 0)*100:.1f}%")

            # 차트 및 가이드 레이아웃
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='주가'))
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='purple', dash='dot'), name='세력평단(VWAP)'))
                fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='orange'), name='20일선'))
                
                # 내 평단가 지시선 추가
                if my_avg_price > 0:
                    fig.add_hline(y=my_avg_price, line_dash="solid", line_color="green", annotation_text="나의 평단")
                
                fig.add_annotation(x=data.index[-1], y=curr_price, text=f"현재가:{curr_price:,.0f}", showarrow=True)
                fig.update_layout(height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader("📝 애널리스트 상세 가이드")
                # 5대 지표 가이드 출력
                for g in guides: st.markdown(g)
                
                # kwonknown 전용 익절 가이드 추가
                if my_avg_price > 0:
                    st.write("---")
                    st.subheader("💡 kwonknown 스윙 팁")
                    profit_rate = ((curr_price - my_avg_price) / my_avg_price) * 100
                    if profit_rate > 3 and rsi_val > 65:
                        st.warning("⚠️ **수익 실현 기회:** 수익권이며 지표가 과열되었습니다. 일부 익절 후 저점 재매수를 고려하세요!")
                    elif profit_rate < 0 and curr_price <= vwap_val * 1.02:
                        st.success("💎 **추가 매수 기회:** 평단 아래지만 세력 평단 근처입니다. 물타기/추매 적기일 수 있습니다.")
                
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
