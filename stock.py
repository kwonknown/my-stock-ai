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
        if c1.button("삼성전자"): st.session_state['search'] = "005930.KS"; st.rerun()
        if c1.button("버티브(VRT)"): st.session_state['search'] = "VRT"; st.rerun()
        if c2.button("마이크론"): st.session_state['search'] = "MU"; st.rerun()
        if c2.button("한미반도체"): st.session_state['search'] = "042700.KQ"; st.rerun()
        if c2.button("브로드컴"): st.session_state['search'] = "AVGO"; st.rerun()
        if c2.button("휴림로"): st.session_state['search'] = "090710.KQ"; st.rerun()
    
    with st.expander("🧪 바이오 & 비만치료"):
        c1, c2 = st.columns(2)
        if c1.button("파마리서치"): st.session_state['search'] = "214450.KQ"; st.rerun()
        if c1.button("일라이릴리"): st.session_state['search'] = "LLY"; st.rerun()
        if c1.button("노보노디스크"): st.session_state['search'] = "NVO"; st.rerun()
        if c2.button("유한양행"): st.session_state['search'] = "000100.KS"; st.rerun()
        if c2.button("리가켐바이오"): st.session_state['search'] = "141080.KQ"; st.rerun()
        if c2.button("바이킹(VKTX)"): st.session_state['search'] = "VKTX"; st.rerun()

    with st.expander("🚗 미래차 & 모빌리티"):
        c1, c2 = st.columns(2)
        if c1.button("테슬라"): st.session_state['search'] = "TSLA"; st.rerun()
        if c1.button("현대차"): st.session_state['search'] = "005380.KS"; st.rerun()
        if c1.button("기아"): st.session_state['search'] = "000270.KS"; st.rerun()
        if c2.button("리비안"): st.session_state['search'] = "RIVN"; st.rerun()
        if c2.button("에코머티"): st.session_state['search'] = "450080.KS"; st.rerun()
        if c2.button("우버"): st.session_state['search'] = "UBER"; st.rerun()

    with st.expander("🛡️ 방산 & 로봇 & 우주"):
        c1, c2 = st.columns(2)
        if c1.button("한화에어로"): st.session_state['search'] = "012450.KS"; st.rerun()
        if c1.button("레인보우로보"): st.session_state['search'] = "277810.KQ"; st.rerun()
        if c1.button("LIG넥스원"): st.session_state['search'] = "079550.KS"; st.rerun()
        if c2.button("아이온큐(IONQ)"): st.session_state['search'] = "IONQ"; st.rerun()
        if c2.button("현대로템"): st.session_state['search'] = "064350.KS"; st.rerun()
        if c2.button("두산로보"): st.session_state['search'] = "454910.KS"; st.rerun()

    st.write("---")
    # 1. 발굴된 리스트를 저장할 세션 상태 초기화
    if 'top_10_list' not in st.session_state:
        st.session_state['top_10_list'] = []

    if st.button("💎 국내/외 정예 보석 TOP 10 발굴"):
        scan_list = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "AMD", "MU", 
            "PLTR", "LLY", "NVO", "VRT", "005930.KS", "000660.KS", "000990.KS", "042700.KQ", 
            "035420.KS", "035720.KS", "214450.KQ", "000100.KS", "068270.KS", "277470.KS", 
            "090430.KS", "192080.KS", "012450.KS", "064350.KS", "005380.KS", "000270.KS", 
            "277810.KQ", "079550.KS", "055550.KS", "105560.KS", "000720.KS"
        ]

        with st.spinner('보석 발굴 중...'):
            all_d = yf.download(scan_list, period="1mo", interval="1d", group_by='ticker', threads=True)
            kr_stocks, us_stocks = [], []
            
            for t in scan_list:
                try:
                    d = calculate_indicators(all_d[t].dropna())
                    if not d.empty:
                        score, _ = calculate_flexible_score(d, {})
                        if score >= 80:
                            item = {'ticker': t, 'score': score}
                            if ".KS" in t or ".KQ" in t: kr_stocks.append(item)
                            else: us_stocks.append(item)
                except: continue
            
            # 상위 5개씩 추출하여 세션 상태에 저장 (영구 보존)
            st.session_state['top_10_list'] = sorted(kr_stocks, key=lambda x: x['score'], reverse=True)[:5] + \
                                             sorted(us_stocks, key=lambda x: x['score'], reverse=True)[:5]

    # 2. 저장된 리스트 출력 (클릭 시 사라지지 않음)
    if st.session_state['top_10_list']:
        st.subheader("🎯 오늘의 정예 보석 (TOP 10)")
        for item in st.session_state['top_10_list']:
            t_code = item['ticker']
            t_score = item['score']
            # 버튼 클릭 시 즉시 검색어로 설정하고 앱 재실행
            if st.button(f"🚀 {t_code} ({t_score}%)", key=f"fixed_top_{t_code}", use_container_width=True):
                st.session_state['search'] = t_code
                st.rerun() # 이 명령어가 즉시 분석 화면으로 전환시킵니다.

    st.write("---")
    # 1. 최근 본 종목 리스트 (중복 키 방어 로직)
    if st.session_state['history']:
        st.subheader("🕒 최근 본 종목")
        # set을 사용하여 중복 종목 출력 방지
        unique_history = []
        for h in st.session_state['history']:
            if h not in unique_history:
                unique_history.append(h)
        
        for h in unique_history:
            # key값에 'hist_' 접두사를 붙여 다른 버튼과 절대 겹치지 않게 합니다.
            if st.button(f"📜 {h}", key=f"hist_btn_{h}", use_container_width=True):
                st.session_state['search'] = h
                st.rerun()

    st.write("---")
    # 2. 직접 검색 및 분석 실행부
    # 여기서도 key를 고유하게 설정합니다.
    manual_input = st.text_input("종목명/티커 입력", key="sidebar_manual_search")
    
    my_p = st.number_input("나의 평단가", value=0.0, key="sidebar_my_price")
    
    if st.button("📊 분석 실행", key="run_analysis_btn"):
        if manual_input:
            st.session_state['search'] = manual_input
        st.rerun()

    # --- [수정된 사이드바 하단 제어부] ---
    st.write("---")
    
    # [핵심] 사용자가 검색창에 직접 입력할 때 사용하는 텍스트 상자
    # key를 부여하여 세션 상태와 직접 연결합니다.
    manual_input = st.text_input("종목명/티커 입력", key="input_field")

    # [중요] 버튼 클릭이나 검색창 입력 등 모든 경로의 '최종 검색어'를 결정하는 로직
    if manual_input and manual_input != st.session_state['search']:
        st.session_state['search'] = manual_input
        st.rerun()

    my_p = st.number_input("나의 평단가", value=0.0)
    
    if st.button("📊 분석 실행"):
        st.rerun()

# --- [메인 화면 분석 로직 시작] ---
# 모든 버튼과 검색창의 결과는 결국 이 한 줄로 모입니다.
ticker = st.session_state['search']

if ticker:
    # 종목 히스토리 업데이트 로직
    if not st.session_state['history'] or ticker != st.session_state['history'][0]:
        st.session_state['history'].insert(0, ticker)
        st.session_state['history'] = st.session_state['history'][:5]

# --- 메인 화면 로직 시작 ---
ticker = st.session_state['search'] # 항상 세션 상태의 최신 티커를 사용합니다.

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
            # 1. 차트 기본 객체 생성
            fig = go.Figure()

            # [주가 캔들스틱] - 시인성 개선
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['Open'], high=data['High'],
                low=data['Low'], close=data['Close'],
                name='주가',
                increasing_line_color='#FF4B4B', # 한국식 빨간색 양봉
                decreasing_line_color='#0077FF'  # 한국식 파란색 음봉
            ))

            # [세력 평단(VWAP)] - 보라색 굵은 점선
            fig.add_trace(go.Scatter(
                x=data.index, y=data['VWAP'],
                line=dict(color='#A020F0', width=2, dash='dot'),
                name='세력평단(VWAP)'
            ))

            # [20일선] - 오렌지색 실선
            fig.add_trace(go.Scatter(
                x=data.index, y=data['MA20'],
                line=dict(color='#FFA500', width=1.5),
                name='20일선'
            ))

            # [거래량 차트] - 하단 보조 지표로 추가 (선택사항)
            # 캔들스틱과 겹치지 않게 별도 레이아웃 설정이 가능합니다.

            # [내 평단가] - 녹색 실선 (입력 시에만 노출)
            if my_p > 0:
                fig.add_hline(
                    y=my_p, 
                    line_dash="solid", 
                    line_color="#00FF00", 
                    line_width=2,
                    annotation_text=f"내 평단: {my_p:,.0f}",
                    annotation_position="top left"
                )

            # 2. 그래프 레이아웃 미세 조정 (디테일 핵심)
            fig.update_layout(
                height=600, # 그래프 높이 확장
                xaxis_rangeslider_visible=False, # 하단 슬라이더 제거하여 공간 확보
                margin=dict(l=0, r=10, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', # 배경 투명화로 앱과 조화
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode="x unified", # 마우스 오버 시 해당 시점 모든 지표 합산 노출
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", y=1.02, 
                    xanchor="right", x=1
                ),
                yaxis=dict(
                    gridcolor='rgba(128, 128, 128, 0.2)', # 그리드선 투명도 조절
                    side="right" # 가격표를 오른쪽으로 배치 (트레이딩뷰 스타일)
                ),
                xaxis=dict(
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    type='category' # 주말/휴장일 공백 제거 (차트 연결성 강화)
                )
            )

            # 3. 차트 출력
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        with col_r:
            st.subheader("🔍 지속 가능성 진단")
            roe = info.get('returnOnEquity', 0) * 100
            if roe > 20: st.success(f"💎 **초우량 지속성:** ROE {roe:.1f}%")
            elif roe > 10: st.success(f"✅ **안정적 지속성:** ROE {roe:.1f}%")
            else: st.info(f"⚖️ **성장성 체크:** ROE {roe:.1f}%")
            
            st.subheader("📝 상세 지표 분석")
            for g in guides: st.markdown(g)
            
            # --- [복구 및 추가된 시뮬레이터 로직] ---
            st.write("---")
            st.subheader("🎯 1-2시간 기대 수익 및 리스크")
            try:
                # 최근 10개 봉의 변동성 계산
                recent_volatility = (data['High'] - data['Low']).tail(10).mean()
                vwap_val = data['VWAP'].iloc[-1]
                ma20_val = data['MA20'].iloc[-1]

                # 목표가 및 리스크 라인 산출
                if curr_p > vwap_val:
                    target_p = curr_p + (recent_volatility * 1.5)
                else:
                    target_p = vwap_val
                
                risk_p = min(ma20_val, vwap_val)
                if curr_p < risk_p:
                    risk_p = data['Low'].tail(5).min()

                expected_gain = ((target_p - curr_p) / curr_p) * 100
                expected_loss = ((risk_p - curr_p) / curr_p) * 100
                
                c_target, c_risk = st.columns(2)
                c_target.metric("🚀 목표 주가", f"{target_p:,.0f}", f"{expected_gain:+.2f}%")
                c_risk.metric("⚠️ 리스크 라인", f"{risk_p:,.0f}", f"{expected_loss:+.2f}%", delta_color="inverse")
            except:
                st.caption("시뮬레이션 데이터 계산 중...")

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
