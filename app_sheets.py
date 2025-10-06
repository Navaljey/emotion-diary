import json
import os
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

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

def calc_total_score(item):
    score = (2 * item["joy"] + 1.5 * item["calmness"] - 
             2 * item["sadness"] - 1.5 * item["anxiety"] - 1.5 * item["anger"] + 50)
    return round(score / 8.5, 2)

# 메인 화면
st.title("📱 감정 일기")
st.caption("AI가 분석하는 나만의 감정 기록 ☁️")

tab1, tab2, tab3 = st.tabs(["✍️ 쓰기", "📊 통계", "📈 그래프"])

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

st.divider()
st.markdown("### 💝 매일 감정을 기록하며 마음을 돌보세요!")
st.caption("🤖 AI가 감정을 분석하고 ☁️ 클라우드에 안전하게 보관합니다")

# 🧠 전문가 조언 탭 추가
tab1, tab2, tab3, tab4 = st.tabs(["✍️ 쓰기", "📊 통계", "📈 그래프", "🧠 전문가 조언"])

# 전문가 조언 탭
with tab4:
    st.subheader("🧠 전문가 조언")
    st.caption("Gemini가 전체 일기 데이터를 분석하여 전문가 시각에서 조언을 제공합니다.")

    # 전체 데이터 불러오기
    data = load_data_from_sheets()
    if not data:
        st.warning("⚠️ 저장된 일기 데이터가 없습니다. 먼저 일기를 작성해주세요.")
        st.stop()

    # 시간순 정렬
    sorted_items = sorted(data.values(), key=lambda x: x["date"])
    diary_texts = "\n\n".join([f"[{item['date']}] {item['content']}" for item in sorted_items])

    experts = {
        "심리상담사": "정서적 안정, 불안, 우울, 감정 조절에 대한 심리상담적 조언을 해줘.",
        "재정관리사": "소비습관, 재무스트레스, 돈 관련 감정이나 계획에 대한 조언을 해줘.",
        "변호사": "법적 문제, 갈등, 권리 보호와 관련된 부분이 있는지 판단하고 조언을 해줘.",
        "의사": "건강, 수면, 식습관, 스트레스와 관련된 의학적 조언을 해줘.",
        "피부관리사": "피부, 외모, 스트레스성 피부 문제와 관련된 조언이 있으면 알려줘.",
        "피트니스 트레이너": "운동, 체력, 에너지 수준, 생활습관과 관련된 피트니스 조언을 해줘.",
        "창업 벤처투자자": "일기 내용 중 도전정신, 창의적 아이디어, 사업 관련 고민이 있다면 조언을 해줘."
    }

    # 분석 실행 버튼
    if st.button("🔍 전문가 조언 분석 시작", type="primary", use_container_width=True):
        with st.spinner("Gemini가 전문가별 분석을 진행 중입니다..."):
            for expert, instruction in experts.items():
                prompt = f"""
                너는 {expert}야. 아래는 한 개인이 기록한 일기 전체 내용이야.
                시간순으로 정리된 감정과 사건을 읽고, 네 전문가 시각으로 의미 있는 조언을 해줘.
                내용 중 {instruction}
                일기 내용:
                ---
                {diary_texts}
                ---
                결과는 짧고 실질적인 조언 위주로.
                """

                response = gemini_chat(prompt)
                st.divider()
                st.markdown(f"### 💬 {expert}의 조언")

                if response and len(response.strip()) > 10:
                    st.write(response.strip())
                else:
                    st.info("🫧 현재 일기 내용에는 특별히 조언할 부분이 없습니다.")


