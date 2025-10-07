import streamlit as st

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(["Tab 1", "Tab 2", "Tab 3", "Tab 4"])

# tab4 컨텍스트에서 작업
with tab4:
    st.write("This is Tab 4 content")

def get_latest_data():
    return [], []

data, items = get_latest_data()  # 이제 에러 발생하지 않음
    
with tab4:
    st.subheader("👨‍⚕️ 전문가 조언")
    st.caption("일기 내용을 시간순으로 분석하여 전문가 관점의 조언을 제공합니다")
    
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기를 작성하면 전문가 조언을 받을 수 있습니다.")
    else:
        st.success(f"📊 최근 {len(items)}개의 일기를 분석합니다")
        
        # 날짜 선택 기능 추가
        st.markdown("### 📅 조언 확인 날짜 선택")
        available_dates = sorted([item['date'] for item in items], reverse=True)
        selected_advice_date = st.selectbox(
            "날짜를 선택하세요 (이전 조언을 다시 볼 수 있습니다)",
            options=available_dates,
            index=0
        )
        
        # 해당 날짜의 저장된 조언 불러오기
        saved_advice = load_expert_advice_from_sheets(selected_advice_date)
        
        if saved_advice:
            st.info(f"💾 {selected_advice_date}에 저장된 조언이 {len(saved_advice)}개 있습니다")
        
        st.divider()
        
        # 전문가 목록을 탭으로 구성
        expert_tabs = st.tabs([
            "🧠 심리상담사",
            "💰 재정관리사", 
            "⚖️ 변호사",
            "🏥 의사",
            "✨ 피부관리사",
            "💪 피트니스",
            "🚀 창업투자",
            "🎨 예술치료",
            "🧬 임상심리",
            "👔 조직/HR"
        ])
        
        # 각 탭별 전문가 조언
        with expert_tabs[0]:
            st.markdown("### 🧠 심리상담사")
            st.caption("감정 패턴과 심리 상태를 분석합니다")
            
            # 저장된 조언이 있으면 표시
            if "심리상담사" in saved_advice:
                st.success(f"📋 저장된 조언 ({saved_advice['심리상담사']['created_at'][:10]})")
                st.markdown(saved_advice["심리상담사"]["advice"])
                st.divider()
            
            if st.button("💬 심리상담사 조언 받기", key="btn_심리상담사", use_container_width=True):
                # 이미지 생성
                if len(items) >= 2:
                    with st.spinner("📊 감정 흐름 그래프 생성 중..."):
                        emotion_flow = create_emotion_flow_chart(items)
                        st.image(emotion_flow, caption="감정 흐름 분석", use_container_width=True)
                    
                    with st.spinner("🕸️ 감정 연관망 생성 중..."):
                        emotion_network = create_emotion_network(items)
                        st.image(emotion_network, caption="감정 연관망", use_container_width=True)
                
                result = get_expert_advice("심리상담사", data)
                if result["has_content"]:
                    st.success("**심리상담사의 조언:**")
                    st.markdown(result["advice"])
                    # Google Sheets에 저장
                    save_expert_advice_to_sheets(selected_advice_date, "심리상담사", 
                                                result["advice"], result["has_content"])
                    st.success("💾 조언이 저장되었습니다")
                else:
                    st.info(result["advice"])
        
        with expert_tabs[1]:
            st.markdown("### 💰 재정관리사")
            st.caption("소비 패턴과 재정 상태를 분석합니다")
            
            if "재정관리사" in saved_advice:
                st.success(f"📋 저장된 조언 ({saved_advice['재정관리사']['created_at'][:10]})")
                st.markdown(saved_advice["재정관리사"]["advice"])
                st.divider()
            
            if st.button("💬 재정관리사 조언 받기", key="btn_재정관리사", use_container_width=True):
                result = get_expert_advice("재정관리사", data)
                if result["has_content"]:
                    st.success("**재정관리사의 조언:**")
                    st.markdown(result["advice"])
                    save_expert_advice_to_sheets(selected_advice_date, "재정관리사",
                                                result["advice"], result["has_content"])
                    st.success("💾 조언이 저장되었습니다")
                else:
                    st.info(result["advice"])
        
        with expert_tabs[2]:
            st.markdown("### ⚖️ 변호사")
            st.caption("법적 이슈와 권리 보호를 검토합니다")
            
            if "변호사" in saved_advice:
                st.success(f"📋 저장된 조언 ({saved_advice['변호사']['created_at'][:10]})")
                st.markdown(saved_advice["변호사"]["advice"])
                st.divider()
            
            if st.button("💬 변호사 조언 받기", key="btn_변호사", use_container_width=True):
                result = get_expert_advice("변호사", data)
                if result["has_content"]:
                    st.success("**변호사의 조언:**")
                    st.markdown(result["advice"])
                    save_expert_advice_to_sheets(selected_advice_date, "변호사",
                                                result["advice"], result["has_content"])
                    st.success("💾 조언이 저장되었습니다")
                else:
                    st.info(result["advice"])
        
        with expert_tabs[3]:
            st.markdown("### 🏥 의사")
            st.caption("건강 상태와 생활습관을 점검합니다")
            
            if "의사" in saved_advice:
                st.success(f"📋 저장된 조언 ({saved_advice['의사']['created_at'][:10]})")
                st.markdown(saved_advice["의사"]["advice"])
                st.divider()
            
            if st.button("💬 의사 조언 받기", key="btn_의사", use_container_width=True):
                result = get_expert_advice("의사", data)
                if result["has_content"]:
                    st.success("**의사의 조언:**")
                    st.markdown(result["advice"])
                    save_expert_advice_to_sheets(selected_advice_date, "의사",
                                                result["advice"], result["has_content"])
                    st.success("💾 조언이 저장되었습니다")
                else:
                    st.info(result["advice"])
        
        with expert_tabs[4]:
            st.markdown("### ✨ 피부관리사")
            st.caption("피부 고민과 관리 방법을 제안합니다")
            
            if "피부관리사" in saved_advice:
                st.success(f"📋 저장된 조언 ({saved_advice['피부관리사']['created_at'][:10]})")
                st.markdown(saved_advice["피부관리사"]["advice"])
                st.divider()
            
            if st.button("💬 피부관리사 조언 받기", key="btn_피부관리사", use_container_width=True):
                result = get_expert_advice("피부관리사", data)
                if result["has_content"]:
                    st.success("**피부관리사의 조언:**")
                    st.markdown(result["advice"])
                    save_expert_advice_to_sheets(selected_advice_date, "피부관리사",
                                                result["advice"], result["has_content"])
                    st.success("💾 조언이 저장되었습니다")
                else:
                    st.info(result["advice"])
        
        with expert_tabs[5]:
            st.markdown("### 💪 피트니스 트레이너")
            st.caption("운동 습관과 체력 관리를 분석합니다")
            
            if "피트니스 트레이너" in saved_advice:
                st.success(f"📋 저장된 조언 ({saved_advice['피트니스 트레이너']['created_at'][:10]})")
                st.markdown(saved_advice["피트니스 트레이너"]["advice"])
                st.divider()
            
            if st.button("💬 피트니스 트레이너 조언 받기", key="btn_피트니스", use_container_width=True):
                result = get_expert_advice("피트니스 트레이너", data)
                if result["has_content"]:
                    st.success("**피트니스 트레이너의 조언:**")
                    st.markdown(result["advice"])
                    save_expert_advice_to_sheets(selected_advice_date, "피트니스 트레이너",
                                                result["advice"], result["has_content"])
                    st.success("💾 조언이 저장되었습니다")
                else:
                    st.info(result["advice"])
        
        with expert_tabs[6]:
            st.markdown("### 🚀 창업 벤처투자자")
            st.caption("비즈니스 기회와 커리어를 분석합니다")
            
            if "창업 벤처투자자" in saved_advice:
                st.success(f"📋 저장된 조언 ({saved_advice['창업 벤처투자자']['created_at'][:10]})")
                st.markdown(saved_advice["창업 벤처투자자"]["advice"])
                st.divider()
            
            if st.button("💬 창업 벤처투자자 조언 받기", key="btn_창업", use_container_width=True):
                # 목표 달성 플로우차트 생성
                if len(items) >= 2:
                    with st.spinner("📊 목표 달성 흐름 분석 중..."):
                        goal_chart = create_goal_flowchart(items)
                        st.image(goal_chart, caption="목표 달성 동기 변화", use_container_width=True)
                
                result = get_expert_advice("창업 벤처투자자", data)
                if result["has_content"]:
                    st.success("**창업 벤처투자자의 조언:**")
                    st.markdown(result["advice"])
                    save_expert_advice_to_sheets(selected_advice_date, "창업 벤처투자자",
                                                result["advice"], result["has_content"])
                    st.success("💾 조언이 저장되었습니다")
                else:
                    st.info(result["advice"])
        
        with expert_tabs[7]:
            st.markdown("### 🎨 예술치료사 / 문학치료사")
            st.caption("창의적 표현과 예술을 통한 치유를 제안합니다")
            
            if "예술치료사" in saved_advice:
                st.success(f"📋 저장된 조언 ({saved_advice['예술치료사']['created_at'][:10]})")
                st.markdown(saved_advice["예술치료사"]["advice"])
                st.divider()
            
            if st.button("💬 예술치료사 조언 받기", key="btn_예술", use_container_width=True):
                # 메타포 이미지 설명 생성
                if len(items) >= 1:
                    metaphor_text = create_metaphor_image_prompt(items)
                    st.info("🎨 **당신의 감정 메타포:**")
                    st.markdown(metaphor_text)
                
                result = get_expert_advice("예술치료사", data)
                st.success("**예술치료사의 조언:**")
                st.markdown(result["advice"])
                save_expert_advice_to_sheets(selected_advice_date, "예술치료사",
                                            result["advice"], True)
                st.success("💾 조언이 저장되었습니다")
        
        with expert_tabs[8]:
            with tab4:
                st.subheader("👨‍⚕️ 전문가 조언")
                st.caption("일기 내용을 시간순으로 분석하여 전문가 관점의 조언을 제공합니다")
    
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기를 작성하면 전문가 조언을 받을 수 있습니다.")
    else:
        st.success(f"📊 최근 {len(items)}개의 일기를 분석합니다")
        
        # 전문가 목록을 탭으로 구성
        expert_tabs = st.tabs([
            "🧠 심리상담사",
            "💰 재정관리사", 
            "⚖️ 변호사",
            "🏥 의사",
            "✨ 피부관리사",
            "💪 피트니스",
            "🚀 창업투자",
            "🎨 예술치료",
            "🧬 임상심리",
            "👔 조직/HR"
        ])
        
        # 각 탭별 전문가 조언
        with expert_tabs[0]:
            st.markdown("### 🧠 심리상담사")
            st.caption("감정 패턴과 심리 상태를 분석합니다")
            if st.button("💬 심리상담사 조언 받기", key="btn_심리상담사", use_container_width=True):
                result = get_expert_advice("심리상담사", data)
                if result["has_content"]:
                    st.success("**심리상담사의 조언:**")
                    st.markdown(result["advice"])
                else:
                    st.info(result["advice"])
        
        with expert_tabs[1]:
            st.markdown("### 💰 재정관리사")
            st.caption("소비 패턴과 재정 상태를 분석합니다")
            if st.button("💬 재정관리사 조언 받기", key="btn_재정관리사", use_container_width=True):
                result = get_expert_advice("재정관리사", data)
                if result["has_content"]:
                    st.success("**재정관리사의 조언:**")
                    st.markdown(result["advice"])
                else:
                    st.info(result["advice"])
        
        with expert_tabs[2]:
            st.markdown("### ⚖️ 변호사")
            st.caption("법적 이슈와 권리 보호를 검토합니다")
            if st.button("💬 변호사 조언 받기", key="btn_변호사", use_container_width=True):
                result = get_expert_advice("변호사", data)
                if result["has_content"]:
                    st.success("**변호사의 조언:**")
                    st.markdown(result["advice"])
                else:
                    st.info(result["advice"])
        
        with expert_tabs[3]:
            st.markdown("### 🏥 의사")
            st.caption("건강 상태와 생활습관을 점검합니다")
            if st.button("💬 의사 조언 받기", key="btn_의사", use_container_width=True):
                result = get_expert_advice("의사", data)
                if result["has_content"]:
                    st.success("**의사의 조언:**")
                    st.markdown(result["advice"])
                else:
                    st.info(result["advice"])
        
        with expert_tabs[4]:
            st.markdown("### ✨ 피부관리사")
            st.caption("피부 고민과 관리 방법을 제안합니다")
            if st.button("💬 피부관리사 조언 받기", key="btn_피부관리사", use_container_width=True):
                result = get_expert_advice("피부관리사", data)
                if result["has_content"]:
                    st.success("**피부관리사의 조언:**")
                    st.markdown(result["advice"])
                else:
                    st.info(result["advice"])
        
        with expert_tabs[5]:
            st.markdown("### 💪 피트니스 트레이너")
            st.caption("운동 습관과 체력 관리를 분석합니다")
            if st.button("💬 피트니스 트레이너 조언 받기", key="btn_피트니스", use_container_width=True):
                result = get_expert_advice("피트니스 트레이너", data)
                if result["has_content"]:
                    st.success("**피트니스 트레이너의 조언:**")
                    st.markdown(result["advice"])
                else:
                    st.info(result["advice"])
        
        with expert_tabs[6]:
            st.markdown("### 🚀 창업 벤처투자자")
            st.caption("비즈니스 기회와 커리어를 분석합니다")
            if st.button("💬 창업 벤처투자자 조언 받기", key="btn_창업", use_container_width=True):
                result = get_expert_advice("창업 벤처투자자", data)
                if result["has_content"]:
                    st.success("**창업 벤처투자자의 조언:**")
                    st.markdown(result["advice"])
                else:
                    st.info(result["advice"])
        
        with expert_tabs[7]:
            st.markdown("### 🎨 예술치료사 / 문학치료사")
            st.caption("창의적 표현과 예술을 통한 치유를 제안합니다")
            if st.button("💬 예술치료사 조언 받기", key="btn_예술", use_container_width=True):
                result = get_expert_advice("예술치료사", data)
                st.success("**예술치료사의 조언:**")
                st.markdown(result["advice"])
        
        with expert_tabs[8]:
            st.markdown("### 🧬 임상심리사 / 정신건강의학과 의사")
            st.caption("정신건강을 임상적 관점에서 평가합니다")
            if st.button("💬 임상심리사 조언 받기", key="btn_임상", use_container_width=True):
                result = get_expert_advice("임상심리사", data)
                st.success("**임상심리사의 조언:**")
                st.markdown(result["advice"])
        
        with expert_tabs[9]:
            st.markdown("### 👔 조직심리 전문가 / HR 코치")
            st.caption("직장 생활과 조직 내 관계를 분석합니다")
            if st.button("💬 조직심리 전문가 조언 받기", key="btn_조직", use_container_width=True):
                result = get_expert_advice("조직심리 전문가", data)
                if result["has_content"]:
                    st.success("**조직심리 전문가의 조언:**")
                    st.markdown(result["advice"])
                else:
                    st.info(result["advice"])
        
        st.divider()
        st.warning("⚠️ **주의사항**: 이 조언은 AI가 생성한 것으로 참고용입니다. 전문적인 상담이나 치료가 필요한 경우 반드시 해당 분야 전문가와 상담하세요.")

st.divider()
import json
import os
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import networkx as nx
from io import BytesIO
import base64

# PWA를 위한 HTML 코드
pwa_html = """
<link rel="manifest" href="data:application/json;charset=utf-8,%7B%22name%22%3A%22%EA%B0%90%EC%A0%95%20%EC%9D%BC%EA%B8%B0%22%2C%22short_name%22%3A%22%EA%B0%90%EC%A0%95%EC%9D%BC%EA%B8%B0%22%2C%22description%22%3A%22AI%EA%B0%80%20%EB%B6%84%EC%84%9D%ED%95%98%EB%8A%94%20%EA%B0%90%EC%A0%95%20%EC%9D%BC%EA%B8%B0%20%EC%95%B1%22%2C%22start_url%22%3A%22%2F%22%2C%22display%22%3A%22standalone%22%2C%22background_color%22%3A%22%23ffffff%22%2C%22theme_color%22%3A%22%23ff6b6b%22%2C%22icons%22%3A%5B%7B%22src%22%3A%22data%3Aimage%2Fsvg%2Bxml%3Bcharset%3Dutf-8%2C%253Csvg%2520xmlns%253D%2522http%253A%252F%252Fwww.w3.org%252F2000%252Fsvg%2522%2520viewBox%253D%25220%25200%2520100%2520100%2522%253E%253Ctext%2520y%253D%2522.9em%2522%2520font-size%253D%252290%2522%253E%25E2%259C%258D%25EF%25B8%258F%253C%252Ftext%253E%253C%252Fsvg%253E%22%2C%22sizes%22%3A%22192x192%22%2C%22type%22%3A%22image%2Fsvg%2Bxml%22%7D%5D%7D">

<style>
@media only screen and (max-width: 768px) {
    .stApp > header { background-color: transparent; }
    .stApp { margin-top: -80px; }
    .main .block-container {
        padding-top: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0.5rem 1rem;
    }
    .stButton > button {
        height: 3rem;
        font-size: 1.1rem;
    }
    [data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e1e5eb;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
}
@supports (-webkit-touch-callout: none) {
    .stApp {
        -webkit-user-select: none;
        -webkit-tap-highlight-color: transparent;
    }
}
</style>
"""

st.set_page_config(
    page_title="감정 일기",
    page_icon="✍️",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': "AI가 분석하는 감정 일기 앱 📱"}
)

st.markdown(pwa_html, unsafe_allow_html=True)

_ = load_dotenv(find_dotenv())

# Gemini API 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # 🔍 사용 가능한 모델 확인 (디버깅)
    st.sidebar.markdown("### 🔍 사용 가능한 Gemini 모델")
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                st.sidebar.success(f"✅ {m.name}")
        
        if not available_models:
            st.sidebar.warning("⚠️ 사용 가능한 모델이 없습니다")
    except Exception as e:
        st.sidebar.error(f"❌ 모델 목록 조회 오류: {e}")
    
    # 첫 번째 사용 가능한 모델 선택
    if available_models:
        model_name = available_models[0].replace('models/', '')
        st.sidebar.info(f"📌 사용 중인 모델: {model_name}")
        model = genai.GenerativeModel(model_name)
    else:
        st.error("❌ 사용 가능한 Gemini 모델이 없습니다. API 키를 확인해주세요.")
        st.stop()
else:
    st.error("🔑 GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

# Google Sheets 연결
@st.cache_resource
def init_google_sheets():
    """Google Sheets 연결 초기화"""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Streamlit secrets에서 인증 정보 가져오기
        credentials_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        
        client = gspread.authorize(credentials)
        
        # 스프레드시트 열기
        SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # 워크시트 가져오기 또는 생성
        try:
            worksheet = spreadsheet.worksheet("diary_data")
        except:
            worksheet = spreadsheet.add_worksheet(title="diary_data", rows=1000, cols=20)
            worksheet.update('A1:K1', [[
                'date', 'content', 'keywords', 'total_score', 
                'joy', 'sadness', 'anger', 'anxiety', 'calmness', 
                'message', 'created_at'
            ]])
        
        return worksheet
    
    except Exception as e:
        st.error(f"❌ Google Sheets 연결 실패: {e}")
        st.info("""
        **설정을 확인해주세요:**
        1. Streamlit Secrets에 gcp_service_account 정보가 있나요?
        2. SPREADSHEET_ID가 올바른가요?
        3. Google Sheets를 서비스 계정과 공유했나요?
        """)
        st.stop()

worksheet = init_google_sheets()

def load_data_from_sheets():
    """Google Sheets에서 데이터 로드 (디버깅 추가)"""
    try:
        st.sidebar.info("🔄 데이터 로딩 중...")
        records = worksheet.get_all_records()
        st.sidebar.success(f"📥 {len(records)}개 레코드 로드됨")
        
        data = {}
        for record in records:
            if record.get('date'):
                date_str = record['date']
                keywords_str = record.get('keywords', '[]')
                try:
                    keywords = json.loads(keywords_str) if isinstance(keywords_str, str) else keywords_str
                except:
                    keywords = keywords_str.split(',') if keywords_str else []
                
                data[date_str] = {
                    'date': date_str,
                    'content': record.get('content', ''),
                    'keywords': keywords,
                    'total_score': float(record.get('total_score', 0)),
                    'joy': int(record.get('joy', 0)),
                    'sadness': int(record.get('sadness', 0)),
                    'anger': int(record.get('anger', 0)),
                    'anxiety': int(record.get('anxiety', 0)),
                    'calmness': int(record.get('calmness', 0)),
                    'message': record.get('message', '')
                }
        
        st.sidebar.success(f"✅ {len(data)}개 일기 로드 완료")
        return data
    except Exception as e:
        st.sidebar.error(f"로드 오류: {e}")
        import traceback
        st.sidebar.error(traceback.format_exc())
        return {}

def save_data_to_sheets(date_str, item_data):
    """Google Sheets에 데이터 저장 (디버깅 추가)"""
    try:
        st.info(f"🔄 저장 시도: {date_str}")
        
        # 현재 데이터 확인
        all_values = worksheet.get_all_values()
        st.info(f"📊 현재 시트 행 수: {len(all_values)}")
        
        row_index = None
        
        # 기존 데이터 찾기
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) > 0 and row[0] == date_str:
                row_index = idx
                st.info(f"📝 기존 데이터 발견: {row_index}행")
                break
        
        # 데이터 준비
        keywords_str = json.dumps(item_data['keywords'], ensure_ascii=False)
        row_data = [
            str(date_str), 
            str(item_data['content']), 
            str(keywords_str), 
            float(item_data['total_score']),
            int(item_data['joy']), 
            int(item_data['sadness']), 
            int(item_data['anger']),
            int(item_data['anxiety']), 
            int(item_data['calmness']), 
            str(item_data['message']),
            datetime.now().isoformat()
        ]
        
        st.info(f"💾 저장할 데이터: {row_data[:3]}...")  # 일부만 표시
        
        # 저장 실행
        if row_index:
            # 기존 행 업데이트
            worksheet.update(f'A{row_index}:K{row_index}', [row_data])
            st.success(f"✅ {row_index}행 업데이트 완료!")
        else:
            # 새 행 추가
            worksheet.append_row(row_data)
            st.success(f"✅ 새 행 추가 완료!")
        
        # 저장 확인
        import time
        time.sleep(1)  # API 반영 대기
        updated_values = worksheet.get_all_values()
        st.success(f"🎉 저장 후 시트 행 수: {len(updated_values)}")
        
        return True
    except Exception as e:
        st.error(f"❌ 저장 오류: {e}")
        import traceback
        st.error(f"상세 오류:\n```\n{traceback.format_exc()}\n```")
        return False

def delete_data_from_sheets(date_str):
    """Google Sheets에서 데이터 삭제"""
    try:
        all_values = worksheet.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if row[0] == date_str:
                worksheet.delete_rows(idx)
                return True
        return False
    except Exception as e:
        st.error(f"삭제 오류: {e}")
        return False

def get_latest_data():
    data = load_data_from_sheets()
    items = sorted(data.values(), key=lambda x: x["date"])[-30:]
    return data, items

def calc_average_total_score(items):
    return round(sum(item["total_score"] for item in items) / len(items), 2) if items else 0

def calc_char_count(items):
    return sum(len(item["content"]) for item in items)

def calc_keyword_count(items):
    keyword_count = {}
    for item in items:
        for keyword in item["keywords"]:
            keyword_count[keyword] = keyword_count.get(keyword, 0) + 1
    return keyword_count

def gemini_chat(prompt):
    try:
        st.info("🤖 Gemini API 호출 중...")
        response = model.generate_content(prompt)
        st.success("✅ Gemini API 응답 받음")
        return response.text
    except Exception as e:
        st.error(f"❌ Gemini API 오류: {e}")
        import traceback
        st.error(f"상세:\n```\n{traceback.format_exc()}\n```")
        return None

def sentiment_analysis(content):
    prompt = f"""
    일기 감정 분석 AI입니다. 다음 일기를 분석해 JSON으로 답변하세요.
    ---
    {content}
    ---
    형식:
    {{
      "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
      "joy": 0-10,
      "sadness": 0-10,
      "anger": 0-10,
      "anxiety": 0-10,
      "calmness": 0-10
    }}
    """
    
    st.info("📊 감정 분석 시작...")
    try:
        response_text = gemini_chat(prompt)
        if response_text:
            st.info(f"📝 Gemini 응답 (처음 100자): {response_text[:100]}...")
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                st.info(f"🔍 추출된 JSON: {json_text[:100]}...")
                result = json.loads(json_text)
                st.success("✅ 감정 분석 완료!")
                return result
            else:
                st.warning("⚠️ JSON 형식을 찾을 수 없음")
    except Exception as e:
        st.error(f"❌ 분석 오류: {e}")
        import traceback
        st.error(traceback.format_exc())
    
    # 기본값 반환
    st.warning("⚠️ 기본 감정 점수 사용")
    return {"keywords": ["일기", "오늘", "하루", "생각", "마음"],
            "joy": 5, "sadness": 3, "anger": 2, "anxiety": 3, "calmness": 4}

def generate_message(today_data, recent_data):
    prompt = f"""
    일기 앱 AI입니다. 따뜻한 메시지를 JSON으로 생성하세요.
    오늘: {today_data}
    최근: {recent_data}
    형식: {{"message": "응원 메시지 😊"}}
    """
    
    st.info("💌 응원 메시지 생성 중...")
    try:
        response_text = gemini_chat(prompt)
        if response_text:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(response_text[start:end])
                st.success("✅ 메시지 생성 완료!")
                return data["message"]
    except Exception as e:
        st.warning(f"⚠️ 메시지 생성 실패: {e}")
    
    return "오늘도 일기를 써주셔서 감사해요! 😊"

# 한글 폰트 설정 (그래프용)
def set_korean_font():
    """한글 폰트 설정"""
    try:
        # 시스템에서 사용 가능한 한글 폰트 찾기
        font_list = [f.name for f in fm.fontManager.ttflist]
        korean_fonts = ['NanumGothic', 'Malgun Gothic', 'AppleGothic', 'DejaVu Sans']
        
        for font in korean_fonts:
            if font in font_list:
                plt.rcParams['font.family'] = font
                break
        else:
            plt.rcParams['font.family'] = 'sans-serif'
        
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass

def create_emotion_flow_chart(items):
    """감정 흐름 그래프 생성 (심리상담사/임상심리사용)"""
    set_korean_font()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    dates = [item['date'][-5:] for item in items[-14:]]  # 최근 14개
    joy = [item['joy'] for item in items[-14:]]
    sadness = [item['sadness'] for item in items[-14:]]
    anger = [item['anger'] for item in items[-14:]]
    anxiety = [item['anxiety'] for item in items[-14:]]
    calmness = [item['calmness'] for item in items[-14:]]
    
    ax.plot(dates, joy, marker='o', label='기쁨', color='#FFD700', linewidth=2)
    ax.plot(dates, sadness, marker='o', label='슬픔', color='#4169E1', linewidth=2)
    ax.plot(dates, anger, marker='o', label='분노', color='#DC143C', linewidth=2)
    ax.plot(dates, anxiety, marker='o', label='불안', color='#FF8C00', linewidth=2)
    ax.plot(dates, calmness, marker='o', label='평온', color='#32CD32', linewidth=2)
    
    ax.set_xlabel('날짜', fontsize=12)
    ax.set_ylabel('감정 점수', fontsize=12)
    ax.set_title('감정 흐름 분석 (최근 2주)', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 이미지를 바이트로 변환
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

def create_emotion_network(items):
    """감정 연관망 그래프 생성 (심리상담사/임상심리사용)"""
    set_korean_font()
    
    # 최근 데이터로 감정 간 상관관계 계산
    recent_items = items[-30:]
    
    emotions = {
        '기쁨': [item['joy'] for item in recent_items],
        '슬픔': [item['sadness'] for item in recent_items],
        '분노': [item['anger'] for item in recent_items],
        '불안': [item['anxiety'] for item in recent_items],
        '평온': [item['calmness'] for item in recent_items]
    }
    
    # 네트워크 그래프 생성
    G = nx.Graph()
    
    emotion_names = list(emotions.keys())
    for emotion in emotion_names:
        G.add_node(emotion)
    
    # 감정 간 상관관계 (간단한 계산)
    import numpy as np
    for i, e1 in enumerate(emotion_names):
        for j, e2 in enumerate(emotion_names):
            if i < j:
                corr = np.corrcoef(emotions[e1], emotions[e2])[0, 1]
                if abs(corr) > 0.3:  # 상관관계가 있는 경우만 연결
                    G.add_edge(e1, e2, weight=abs(corr))
    
    fig, ax = plt.subplots(figsize=(10, 8))
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # 노드 그리기
    node_colors = ['#FFD700', '#4169E1', '#DC143C', '#FF8C00', '#32CD32']
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                          node_size=3000, alpha=0.9, ax=ax)
    
    # 엣지 그리기
    edges = G.edges()
    weights = [G[u][v]['weight'] for u, v in edges]
    nx.draw_networkx_edges(G, pos, width=[w*5 for w in weights], 
                          alpha=0.5, ax=ax)
    
    # 레이블 그리기
    nx.draw_networkx_labels(G, pos, font_size=14, 
                           font_weight='bold', ax=ax)
    
    ax.set_title('감정 연관망 분석', fontsize=16, fontweight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

def create_metaphor_image_prompt(items):
    """예술치료사용 메타포 이미지 프롬프트 생성"""
    recent_items = items[-7:]
    
    # 주요 감정과 키워드 추출
    all_keywords = []
    emotions_summary = {'joy': 0, 'sadness': 0, 'anger': 0, 'anxiety': 0, 'calmness': 0}
    
    for item in recent_items:
        all_keywords.extend(item['keywords'])
        for emotion in emotions_summary:
            emotions_summary[emotion] += item[emotion]
    
    # 가장 많이 나타난 감정
    dominant_emotion = max(emotions_summary, key=emotions_summary.get)
    
    emotion_metaphors = {
        'joy': '밝은 햇살, 피어나는 꽃, 날아오르는 새',
        'sadness': '비 내리는 하늘, 고요한 호수, 떨어지는 나뭇잎',
        'anger': '타오르는 불꽃, 폭풍우, 거친 파도',
        'anxiety': '어두운 미로, 꼬인 실타래, 흔들리는 불꽃',
        'calmness': '잔잔한 바다, 평화로운 숲, 구름 위의 하늘'
    }
    
    prompt = f"""
당신의 최근 감정 상태를 상징하는 이미지 메타포:

주요 감정: {dominant_emotion}
상징: {emotion_metaphors[dominant_emotion]}

이 이미지는 당신의 무의식에서 표현되는 감정의 상징입니다.
{emotion_metaphors[dominant_emotion]}와 같은 이미지를 통해 
내면의 감정을 시각화하고 이해할 수 있습니다.
"""
    
    return prompt

def create_goal_flowchart(items):
    """창업투자자용 목표 달성 흐름차트"""
    set_korean_font()
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 최근 아이템에서 키워드 분석
    recent_items = items[-14:]
    
    dates = [item['date'][-5:] for item in recent_items]
    scores = [item['total_score'] for item in recent_items]
    
    # 목표 달성도 시각화 (감정 점수를 동기/에너지 수준으로 해석)
    ax.plot(dates, scores, marker='o', color='#1E90FF', linewidth=3, 
            markersize=10, label='동기/에너지 수준')
    
    # 평균선 추가
    avg_score = sum(scores) / len(scores)
    ax.axhline(y=avg_score, color='r', linestyle='--', linewidth=2, 
               alpha=0.7, label=f'평균: {avg_score:.1f}')
    
    # 목표선 (8점)
    ax.axhline(y=8, color='g', linestyle='--', linewidth=2, 
               alpha=0.5, label='목표 수준: 8.0')
    
    # 영역 색칠
    ax.fill_between(range(len(dates)), scores, avg_score, 
                    where=[s >= avg_score for s in scores],
                    alpha=0.3, color='green', label='상승 구간')
    ax.fill_between(range(len(dates)), scores, avg_score,
                    where=[s < avg_score for s in scores],
                    alpha=0.3, color='red', label='하락 구간')
    
    ax.set_xlabel('날짜', fontsize=12)
    ax.set_ylabel('동기/에너지 수준', fontsize=12)
    ax.set_title('목표 달성 동기 변화 분석', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 10])
    plt.xticks(range(len(dates)), dates, rotation=45)
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

def save_expert_advice_to_sheets(date_str, expert_type, advice, has_content):
    """전문가 조언을 Google Sheets에 저장"""
    try:
        # 기존 조언 확인
        all_values = expert_worksheet.get_all_values()
        row_index = None
        
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) >= 2 and row[0] == date_str and row[1] == expert_type:
                row_index = idx
                break
        
        row_data = [
            str(date_str),
            str(expert_type),
            str(advice),
            str(has_content),
            datetime.now().isoformat()
        ]
        
        if row_index:
            expert_worksheet.update(f'A{row_index}:E{row_index}', [row_data])
        else:
            expert_worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        st.error(f"조언 저장 오류: {e}")
        return False

def load_expert_advice_from_sheets(date_str):
    """특정 날짜의 전문가 조언 불러오기"""
    try:
        records = expert_worksheet.get_all_records()
        advice_data = {}
        
        for record in records:
            if record.get('date') == date_str:
                expert_type = record.get('expert_type', '')
                advice_data[expert_type] = {
                    'advice': record.get('advice', ''),
                    'has_content': record.get('has_content', 'False') == 'True',
                    'created_at': record.get('created_at', '')
                }
        
        return advice_data
    except Exception as e:
        st.error(f"조언 로드 오류: {e}")
        return {}

def get_expert_advice(expert_type, diary_data):
    """전문가 조언 생성"""
    
    # 일기 데이터를 시간순으로 정렬
    sorted_diaries = sorted(diary_data.values(), key=lambda x: x['date'])
    
    # 최근 30개 일기만 분석 (너무 많으면 토큰 제한)
    recent_diaries = sorted_diaries[-30:]
    
    # 일기 요약 생성
    diary_summary = []
    for diary in recent_diaries:
        summary = f"날짜: {diary['date']}, 내용: {diary['content'][:100]}..., 감정점수: {diary['total_score']}"
        diary_summary.append(summary)
    
    diary_text = "\n".join(diary_summary)
    
    # 전문가별 프롬프트
    expert_prompts = {
        "심리상담사": f"""
당신은 경험 많은 심리상담사입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들을 분석하여:
1. 감정 패턴과 심리 상태 분석
2. 반복되는 스트레스 요인 파악
3. 심리적 건강을 위한 구체적 조언
4. 필요시 전문가 상담 권유

조언할 내용이 있으면 따뜻하고 공감적인 톤으로 작성하세요.
조언할 특별한 내용이 없다면 "현재 심리적으로 안정적인 상태로 보입니다."라고 답변하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true/false}}
""",
        "재정관리사": f"""
당신은 전문 재정관리사입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들에서 금전, 소비, 지출, 저축, 투자 등 재정 관련 내용을 찾아 분석하여:
1. 소비 패턴 분석
2. 재정 스트레스 요인 파악
3. 재정 건강을 위한 구체적 조언
4. 저축이나 지출 개선 방안

재정 관련 내용이 있으면 전문적이고 실용적인 조언을 제공하세요.
재정 관련 내용이 없거나 미미하다면 "일기에서 재정 관련 내용을 찾을 수 없습니다."라고 답변하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true/false}}
""",
        "변호사": f"""
당신은 경험 많은 변호사입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들에서 법적 문제, 계약, 분쟁, 권리 침해 등 법률 관련 내용을 찾아 분석하여:
1. 잠재적 법적 이슈 파악
2. 권리 보호 방안
3. 법적 주의사항
4. 필요시 전문 법률 상담 권유

법적 문제가 있으면 신중하고 전문적인 조언을 제공하세요.
법적 문제가 없다면 "일기에서 법적 조언이 필요한 내용을 찾을 수 없습니다."라고 답변하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true/false}}
""",
        "의사": f"""
당신은 경험 많은 종합병원 의사입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들에서 건강, 질병, 증상, 통증, 수면 등 의학 관련 내용을 찾아 분석하여:
1. 건강 상태 패턴 분석
2. 주의해야 할 증상
3. 생활습관 개선 조언
4. 필요시 병원 진료 권유

건강 관련 내용이 있으면 의학적으로 신중한 조언을 제공하세요.
건강 문제가 없다면 "일기에서 특별한 건강 문제를 찾을 수 없습니다. 건강한 상태를 유지하세요."라고 답변하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true/false}}
""",
        "피부관리사": f"""
당신은 전문 피부관리사입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들에서 피부, 외모, 미용, 화장품, 피부 트러블 등 관련 내용을 찾아 분석하여:
1. 피부 고민 파악
2. 생활습관과 피부 상태 연관성 분석
3. 피부 관리 조언
4. 제품 사용이나 관리 팁

피부 관련 내용이 있으면 전문적이고 실용적인 조언을 제공하세요.
피부 관련 내용이 없다면 "일기에서 피부 관련 고민을 찾을 수 없습니다."라고 답변하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true/false}}
""",
        "피트니스 트레이너": f"""
당신은 경험 많은 피트니스 퍼스널 트레이너입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들에서 운동, 다이어트, 체력, 신체활동 등 관련 내용을 찾아 분석하여:
1. 운동 습관 분석
2. 체력 및 건강 상태 파악
3. 운동 루틴 제안
4. 동기부여 메시지

운동 관련 내용이 있으면 실천 가능한 조언을 제공하세요.
운동 관련 내용이 없다면 "일기에서 운동 관련 내용을 찾을 수 없습니다. 규칙적인 운동을 시작해보세요!"라고 답변하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true/false}}
""",
        "창업 벤처투자자": f"""
당신은 성공한 창업가이자 벤처투자자입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들에서 사업, 창업, 아이디어, 커리어, 직장, 프로젝트 등 관련 내용을 찾아 분석하여:
1. 비즈니스 기회 포착
2. 창업 아이디어 검증
3. 커리어 개발 조언
4. 실행 가능한 다음 단계 제안

창업이나 비즈니스 관련 내용이 있으면 실용적이고 구체적인 조언을 제공하세요.
관련 내용이 없다면 "일기에서 창업이나 비즈니스 관련 내용을 찾을 수 없습니다."라고 답변하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true/false}}
""",
        "예술치료사": f"""
당신은 경험 많은 예술치료사이자 문학치료사입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들을 창의적이고 예술적 관점에서 분석하여:
1. 글쓰기를 통한 감정 표현 패턴 분석
2. 은유와 상징 해석
3. 창의적 표현 활동 제안 (그림, 음악, 글쓰기 등)
4. 예술을 통한 치유 방법 제시

예술적 표현이나 창의적 활동 관련 내용이 있으면 감성적이고 창의적인 조언을 제공하세요.
관련 내용이 없어도 "일기를 통해 자신을 표현하는 것 자체가 훌륭한 예술 활동입니다."라는 긍정적 메시지를 포함하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true}}
""",
        "임상심리사": f"""
당신은 임상심리사이자 정신건강의학과 전문의입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들을 임상적 관점에서 분석하여:
1. 정신건강 상태 평가 (우울, 불안, 스트레스 수준)
2. 병리적 징후 여부 확인
3. 인지 패턴과 사고 왜곡 파악
4. 전문적 치료나 약물 치료 필요성 판단
5. 자가 관리 방법과 대처 기술 제안

심각한 정신건강 문제가 의심되면 반드시 전문의 상담을 권유하세요.
정상 범위라면 "현재 정신건강은 양호한 상태입니다."라고 답변하되, 예방적 관리 방법도 제시하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true}}
""",
        "조직심리 전문가": f"""
당신은 조직심리 전문가이자 HR 코치입니다.
다음은 사용자의 최근 일기 내용입니다 (시간순):

{diary_text}

위 일기들에서 직장, 조직, 팀워크, 리더십, 대인관계, 업무 스트레스 등 관련 내용을 찾아 분석하여:
1. 조직 내 관계 패턴 분석
2. 업무 스트레스 요인 파악
3. 리더십 및 커뮤니케이션 개선 방안
4. 워크라이프 밸런스 조언
5. 경력 개발 및 성장 전략

직장 관련 내용이 있으면 조직심리학 관점에서 구체적인 조언을 제공하세요.
직장 관련 내용이 없다면 "일기에서 조직이나 직장 관련 내용을 찾을 수 없습니다."라고 답변하세요.

JSON 형식으로 답변: {{"advice": "조언 내용", "has_content": true/false}}
"""
    }
    
    prompt = expert_prompts.get(expert_type, "")
    
    try:
        with st.spinner(f'🤖 {expert_type} 분석 중...'):
            response_text = gemini_chat(prompt)
            if response_text:
                # JSON 추출
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_text = response_text[start:end]
                    result = json.loads(json_text)
                    return result
    except Exception as e:
        st.error(f"분석 오류: {e}")
    
    return {"advice": "조언을 생성할 수 없습니다.", "has_content": False}

def calc_total_score(item):
    score = (2 * item["joy"] + 1.5 * item["calmness"] - 
             2 * item["sadness"] - 1.5 * item["anxiety"] - 1.5 * item["anger"] + 50)
    return round(score / 8.5, 2)

# 메인 화면
st.title("📱 감정 일기")
st.caption("AI가 분석하는 나만의 감정 기록 ☁️")

tab1, tab2, tab3, tab4 = st.tabs(["✍️ 쓰기", "📊 통계", "📈 그래프", "👨‍⚕️ 전문가 조언"])

with tab1:
    st.subheader("오늘의 마음")
    
    data, items = get_latest_data()
    
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    
    selected_date = st.date_input("📅 날짜", value=st.session_state.selected_date)
    st.session_state.selected_date = selected_date
    date_str = selected_date.strftime("%Y-%m-%d")
    
    default_content = ""
    total_score = None
    message = None
    diary_exists = date_str in data
    
    if diary_exists:
        default_content = data[date_str]["content"]
        total_score = data[date_str]["total_score"]
        message = data[date_str]["message"]
    
    if data:
        st.success(f"☁️ {len(data)}개의 일기가 클라우드에 저장되어 있습니다")
    
    content = st.text_area(
        "📝 오늘 하루는 어땠나요?", 
        default_content, 
        height=200,
        placeholder="자유롭게 마음을 적어보세요..."
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        save_clicked = st.button("💾 저장하기", type="primary", use_container_width=True)
    with col2:
        if diary_exists:
            if st.button("🗑️", help="일기 삭제"):
                st.session_state.confirm_delete = date_str
                st.rerun()
        else:
            if st.button("🗑️", help="내용 지우기"):
                st.rerun()
    
    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        delete_date = st.session_state.confirm_delete
        st.warning(f"⚠️ {delete_date} 일기를 삭제하시겠습니까?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ 예", type="primary", key="yes"):
                if delete_data_from_sheets(delete_date):
                    st.success("🗑️ 삭제되었습니다.")
                del st.session_state.confirm_delete
                st.rerun()
        with col_no:
            if st.button("❌ 아니오", key="no"):
                del st.session_state.confirm_delete
                st.rerun()
        save_clicked = False
    
    if save_clicked:
        if content.strip():
            with st.spinner('🤖 AI 분석 중...'):
                analyzed = sentiment_analysis(content)
                data, items = get_latest_data()
                
                today_data = {
                    "date": date_str, "keywords": analyzed["keywords"],
                    "joy": analyzed["joy"], "sadness": analyzed["sadness"],
                    "anger": analyzed["anger"], "anxiety": analyzed["anxiety"],
                    "calmness": analyzed["calmness"],
                }
                
                recent_data = [{
                    "date": item["date"], "keywords": item["keywords"],
                    "joy": item["joy"], "sadness": item["sadness"],
                    "anger": item["anger"], "anxiety": item["anxiety"],
                    "calmness": item["calmness"],
                } for item in items[-7:]]
                
                message = generate_message(today_data, recent_data)
                
                new_item = {
                    "date": date_str, "content": content, 
                    "keywords": analyzed["keywords"],
                    "total_score": calc_total_score(analyzed),
                    "joy": analyzed["joy"], "sadness": analyzed["sadness"],
                    "anger": analyzed["anger"], "anxiety": analyzed["anxiety"],
                    "calmness": analyzed["calmness"], "message": message,
                }
                
                if save_data_to_sheets(date_str, new_item):
                    st.success("✅ 저장되었습니다!")
                    st.balloons()
                    st.rerun()
        else:
            st.warning("⚠️ 내용을 입력해주세요!")
    
    if 'confirm_delete' not in st.session_state:
        st.divider()
        
        if total_score is not None:
            if total_score >= 8:
                emoji, color = "😄", "green"
            elif total_score >= 6:
                emoji, color = "😊", "blue"
            elif total_score >= 4:
                emoji, color = "😐", "orange"
            else:
                emoji, color = "😢", "red"
            
            st.markdown(f"### 🎯 감정 점수: **:{color}[{total_score}/10]** {emoji}")
            
            if date_str in data:
                item = data[date_str]
                st.write("**🎭 세부 분석:**")
                cols = st.columns(5)
                emotions = [
                    ("😄", "기쁨", item["joy"]),
                    ("😢", "슬픔", item["sadness"]),
                    ("😡", "분노", item["anger"]),
                    ("😰", "불안", item["anxiety"]),
                    ("😌", "평온", item["calmness"])
                ]
                for i, (e, n, s) in enumerate(emotions):
                    with cols[i]:
                        st.metric(f"{e} {n}", f"{s}")
                
                if message:
                    st.success(f"💌 {message}")
        else:
            st.info("💡 일기를 작성하면 AI가 분석해드려요!")

with tab2:
    st.subheader("📊 통계")
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 첫 일기를 써보세요! ✨")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📈 평균 점수", f"{calc_average_total_score(items)}점")
            st.metric("✏️ 총 글자", f"{calc_char_count(items):,}자")
        with col2:
            st.metric("📚 일기 수", f"{len(items)}개")
            st.metric("📅 활동 월", f"{len(set([i['date'][:7] for i in items]))}개월")
        
        st.divider()
        st.write("🏷️ **키워드 TOP 10**")
        keywords = calc_keyword_count(items)
        if keywords:
            sorted_kw = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:10]
            for i, (kw, cnt) in enumerate(sorted_kw):
                if i < 3:
                    st.markdown(f"### {['🥇','🥈','🥉'][i]} **{kw}** `{cnt}회`")
                else:
                    st.markdown(f"**{i+1}.** {kw} `{cnt}회`")

with tab3:
    st.subheader("📈 그래프")
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기 2개 이상 필요")
    else:
        st.write("**🎯 감정 점수 변화**")
        scores = [{"날짜": i["date"][5:], "점수": i["total_score"]} for i in items[-14:]]
        st.line_chart(scores, x="날짜", y="점수", height=300)
        
        st.write("**🎭 감정별 변화**")
        emotions = [{
            "날짜": i["date"][5:],
            "😄기쁨": i["joy"], "😌평온": i["calmness"],
            "😰불안": i["anxiety"], "😢슬픔": i["sadness"], "😡분노": i["anger"],
        } for i in items[-14:]]
        st.area_chart(emotions, x="날짜", 
                     y=["😄기쁨", "😌평온", "😰불안", "😢슬픔", "😡분노"], height=300)

with tab4:
    st.subheader("👨‍⚕️ 전문가 조언")
    st.caption("일기 내용을 분석하여 전문가 관점의 조언을 제공합니다")
    
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기를 작성하면 전문가 조언을 받을 수 있습니다.")
    else:
        st.success(f"📊 {len(items)}개의 일기를 분석합니다")
        
        # 전문가 목록
        experts = {
            "🧠 심리상담사": "심리상담사",
            "💰 재정관리사": "재정관리사",
            "⚖️ 변호사": "변호사",
            "🏥 의사": "의사",
            "✨ 피부관리사": "피부관리사",
            "💪 피트니스 트레이너": "피트니스 트레이너",
            "🚀 창업 벤처투자자": "창업 벤처투자자"
        }
        
        st.write("### 📋 전문가 선택")
        st.write("분석받고 싶은 전문가를 선택하세요:")
        
        # 전문가별 조언 표시
        for display_name, expert_type in experts.items():
            with st.expander(f"{display_name}", expanded=False):
                if st.button(f"💬 {expert_type} 조언 받기", key=f"btn_{expert_type}"):
                    result = get_expert_advice(expert_type, data)
                    
                    if result["has_content"]:
                        st.success(f"**{expert_type}의 조언:**")
                        st.markdown(result["advice"])
                    else:
                        st.info(result["advice"])
        
        st.divider()
        st.warning("⚠️ **주의사항**: 이 조언은 AI가 생성한 것으로 참고용입니다. 전문적인 상담이나 치료가 필요한 경우 반드시 해당 분야 전문가와 상담하세요.")

st.divider()
st.markdown("### 💝 매일 감정을 기록하며 마음을 돌보세요!")
st.caption("🤖 AI가 감정을 분석하고 ☁️ 클라우드에 안전하게 보관합니다")









