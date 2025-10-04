import json
import os
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# PWA를 위한 HTML 코드
pwa_html = """
<link rel="manifest" href="data:application/json;charset=utf-8,%7B%22name%22%3A%22%EA%B0%90%EC%A0%95%20%EC%9D%BC%EA%B8%B0%22%2C%22short_name%22%3A%22%EA%B0%90%EC%A0%95%EC%9D%BC%EA%B8%B0%22%2C%22description%22%3A%22AI%EA%B0%80%20%EB%B6%84%EC%84%9D%ED%95%98%EB%8A%94%20%EA%B0%90%EC%A0%95%20%EC%9D%BC%EA%B8%B0%20%EC%95%B1%22%2C%22start_url%22%3A%22%2F%22%2C%22display%22%3A%22standalone%22%2C%22background_color%22%3A%22%23ffffff%22%2C%22theme_color%22%3A%22%23ff6b6b%22%2C%22icons%22%3A%5B%7B%22src%22%3A%22data%3Aimage%2Fsvg%2Bxml%3Bcharset%3Dutf-8%2C%253Csvg%2520xmlns%253D%2522http%253A%252F%252Fwww.w3.org%252F2000%252Fsvg%2522%2520viewBox%253D%25220%25200%2520100%2520100%2522%253E%253Ctext%2520y%253D%2522.9em%2522%2520font-size%253D%252290%2522%253E%25E2%259C%258D%25EF%25B8%258F%253C%252Ftext%253E%253C%252Fsvg%253E%22%2C%22sizes%22%3A%22192x192%22%2C%22type%22%3A%22image%2Fsvg%2Bxml%22%7D%5D%7D">

<style>
/* 모바일 최적화 CSS */
@media only screen and (max-width: 768px) {
    .stApp > header {
        background-color: transparent;
    }
    
    .stApp {
        margin-top: -80px;
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
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

# Streamlit 페이지 설정
st.set_page_config(
    page_title="감정 일기",
    page_icon="✍️",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "AI가 분석하는 감정 일기 앱 📱"
    }
)

st.markdown(pwa_html, unsafe_allow_html=True)

_ = load_dotenv(find_dotenv())

# Google AI Studio API 키 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("🔑 GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

# Google Sheets 설정
@st.cache_resource
def init_google_sheets():
    """Google Sheets 연결 초기화"""
    try:
        # Streamlit secrets에서 서비스 계정 정보 가져오기
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # secrets.toml에서 서비스 계정 정보 로드
        credentials_dict = dict(st.secrets["gcp_service_account"])
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_dict, scope
        )
        
        client = gspread.authorize(credentials)
        
        # 스프레드시트 ID는 secrets에 저장하거나 여기에 직접 입력
        SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "YOUR_SPREADSHEET_ID")
        
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
        except:
            st.error("❌ Google Sheets에 접근할 수 없습니다. 스프레드시트 ID와 공유 설정을 확인해주세요.")
            st.stop()
        
        # 워크시트 가져오기 또는 생성
        try:
            worksheet = spreadsheet.worksheet("diary_data")
        except:
            worksheet = spreadsheet.add_worksheet(title="diary_data", rows=1000, cols=20)
            # 헤더 설정
            worksheet.update('A1:K1', [[
                'date', 'content', 'keywords', 'total_score', 
                'joy', 'sadness', 'anger', 'anxiety', 'calmness', 
                'message', 'created_at'
            ]])
        
        return worksheet
    
    except Exception as e:
        st.error(f"Google Sheets 연결 실패: {e}")
        st.info("💡 설정 방법:\n1. Google Cloud에서 서비스 계정 생성\n2. Google Sheets API 활성화\n3. secrets.toml에 인증 정보 추가")
        st.stop()

# Google Sheets 초기화
worksheet = init_google_sheets()

def load_data_from_sheets():
    """Google Sheets에서 데이터 로드"""
    try:
        records = worksheet.get_all_records()
        data = {}
        for record in records:
            if record.get('date'):  # 날짜가 있는 행만 처리
                date_str = record['date']
                # keywords를 문자열에서 리스트로 변환
                keywords_str = record.get('keywords', '[]')
                if isinstance(keywords_str, str):
                    try:
                        keywords = json.loads(keywords_str)
                    except:
                        keywords = keywords_str.split(',') if keywords_str else []
                else:
                    keywords = keywords_str
                
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
        return data
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return {}

def save_data_to_sheets(date_str, item_data):
    """Google Sheets에 데이터 저장 (개별 행)"""
    try:
        # 기존 행 찾기
        all_values = worksheet.get_all_values()
        row_index = None
        
        for idx, row in enumerate(all_values[1:], start=2):  # 헤더 제외
            if row[0] == date_str:  # 날짜 컬럼 확인
                row_index = idx
                break
        
        # keywords를 JSON 문자열로 변환
        keywords_str = json.dumps(item_data['keywords'], ensure_ascii=False)
        
        row_data = [
            date_str,
            item_data['content'],
            keywords_str,
            item_data['total_score'],
            item_data['joy'],
            item_data['sadness'],
            item_data['anger'],
            item_data['anxiety'],
            item_data['calmness'],
            item_data['message'],
            datetime.now().isoformat()
        ]
        
        if row_index:
            # 기존 행 업데이트
            worksheet.update(f'A{row_index}:K{row_index}', [row_data])
        else:
            # 새 행 추가
            worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        st.error(f"데이터 저장 오류: {e}")
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
        st.error(f"데이터 삭제 오류: {e}")
        return False

def get_latest_data():
    """최신 데이터를 로드하는 함수"""
    data = load_data_from_sheets()
    items = []
    for item in data.values():
        items.append(item)
    items.sort(key=lambda x: x["date"])
    items = items[-30:]
    return data, items

def calc_average_total_score(items):
    if len(items) == 0:
        return 0
    total_score_sum = sum(item["total_score"] for item in items)
    return round(total_score_sum / len(items), 2)

def calc_char_count(items):
    return sum(len(item["content"]) for item in items)

def calc_keyword_count(items):
    keyword_count = {}
    for item in items:
        for keyword in item["keywords"]:
            keyword_count[keyword] = keyword_count.get(keyword, 0) + 1
    return keyword_count

def gemini_chat(prompt):
    """Gemini API를 사용하여 텍스트 생성"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API 오류: {e}")
        return None

def sentiment_analysis(content):
    prompt = f"""
    당신은 일기 애플리케이션의 감정 분석 AI입니다.
    다음은 사용자가 작성한 일기의 본문입니다.
    ---
    {content}
    ---
    이 본문을 토대로 아래 데이터를 생성해 JSON으로 답변하세요.
    - 일기에서 추출한 핵심 키워드 5개 (keywords)
    - 감정 점수 (0~10점)
      - 기쁨 (joy)
      - 슬픔 (sadness)
      - 분노 (anger)
      - 불안 (anxiety)
      - 평온 (calmness)
    
    다음은 답변 JSON형식의 예시입니다.
    {{
      "keywords": ["축구", "슛", "친구", "즐거웠다", "신난다"],
      "joy": 8,
      "sadness": 0,
      "anger": 0,
      "anxiety": 0,
      "calmness": 1
    }}
    
    반드시 유효한 JSON 형식으로만 답변해주세요.
    """
    
    try:
        response_text = gemini_chat(prompt)
        if response_text:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_text = response_text[start_idx:end_idx]
            data = json.loads(json_text)
            return data
        else:
            return {
                "keywords": ["일기", "오늘", "하루", "생각", "마음"],
                "joy": 5, "sadness": 3, "anger": 2, "anxiety": 3, "calmness": 4
            }
    except Exception as e:
        return {
            "keywords": ["일기", "오늘", "하루", "생각", "마음"],
            "joy": 5, "sadness": 3, "anger": 2, "anxiety": 3, "calmness": 4
        }

def generate_message(today_data, recent_data):
    prompt = f"""
    당신은 일기 애플리케이션의 감정 분석 AI입니다.
    오늘 일기 데이터: {today_data}
    최근 7개 일기 데이터: {recent_data}
    
    위 데이터를 활용해 다음과 같은 내용을 포함한 메시지를 생성해 JSON으로 답변하세요.
    - 최근 감정 상태의 변화를 알려 주는 내용
    - 오늘의 일기에 대해 위로와 공감하는 내용
    - 계속 일기를 쓸 수 있도록 응원하는 내용
    - 적당한 이모지를 섞어 친근한 느낌
    
    예시: {{ "message": "오늘도 좋은 하루를 보내셨네요 😄" }}
    
    반드시 유효한 JSON 형식으로만 답변해주세요.
    """
    
    try:
        response_text = gemini_chat(prompt)
        if response_text:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_text = response_text[start_idx:end_idx]
            data = json.loads(json_text)
            return data["message"]
        else:
            return "오늘도 일기를 써주셔서 감사해요! 😊"
    except:
        return "오늘도 일기를 써주셔서 감사해요! 😊"

def calc_total_score(item):
    score = (
        2 * item["joy"] + 1.5 * item["calmness"] - 
        2 * item["sadness"] - 1.5 * item["anxiety"] - 1.5 * item["anger"] + 50
    )
    return round(score / 8.5, 2)

# 메인 화면
st.title("📱 감정 일기")
st.caption("AI가 분석하는 나만의 감정 기록 (☁️ 클라우드 저장)")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["✍️ 쓰기", "📊 통계", "📈 그래프"])

with tab1:
    st.subheader("오늘의 마음")
    
    # 최신 데이터 로드
    data, items = get_latest_data()
    
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    
    selected_date = st.date_input(
        "📅 날짜", 
        value=st.session_state.selected_date,
        help="일기를 쓸 날짜를 선택하세요"
    )
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
        placeholder="자유롭게 마음을 적어보세요...\n• 좋았던 일\n• 힘들었던 일\n• 느낀 감정들\n• 내일의 다짐"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        save_clicked = st.button("💾 저장하기", type="primary", use_container_width=True)
    with col2:
        if diary_exists:
            delete_clicked = st.button("🗑️", help="일기 삭제하기")
            if delete_clicked:
                st.session_state.confirm_delete = date_str
                st.rerun()
        else:
            if st.button("🗑️", help="내용 지우기"):
                st.rerun()
    
    # 삭제 확인
    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        delete_date = st.session_state.confirm_delete
        st.warning(f"⚠️ {delete_date} 일기를 정말로 삭제하시겠습니까?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ 예, 삭제합니다", type="primary", key="confirm_yes"):
                if delete_data_from_sheets(delete_date):
                    st.success("🗑️ 일기가 삭제되었습니다.")
                del st.session_state.confirm_delete
                st.rerun()
        with col_no:
            if st.button("❌ 아니오, 취소", key="confirm_no"):
                del st.session_state.confirm_delete
                st.rerun()
        save_clicked = False
    
    if save_clicked:
        if content.strip():
            with st.spinner('🤖 AI가 감정을 분석 중...'):
                analyzed = sentiment_analysis(content)
                
                current_data, current_items = get_latest_data()
                recent_items = current_items[-7:]
                
                today_data = {
                    "date": date_str,
                    "keywords": analyzed["keywords"],
                    "joy": analyzed["joy"], "sadness": analyzed["sadness"],
                    "anger": analyzed["anger"], "anxiety": analyzed["anxiety"],
                    "calmness": analyzed["calmness"],
                }
                
                recent_data = [{
                    "date": item["date"], "keywords": item["keywords"],
                    "joy": item["joy"], "sadness": item["sadness"],
                    "anger": item["anger"], "anxiety": item["anxiety"],
                    "calmness": item["calmness"],
                } for item in recent_items]
                
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
                    st.success("✅ 일기가 클라우드에 저장되었습니다!")
                    st.balloons()
                    st.rerun()
        else:
            st.warning("⚠️ 일기 내용을 입력해주세요!")
    
    # 결과 표시
    if 'confirm_delete' not in st.session_state:
        st.divider()
        
        if total_score is not None:
            if total_score >= 8:
                emoji, color = "😄", "green"
            elif total_score >= 6:
                emoji, color = "😊", "blue"  
            elif total_score >= 4:
                emoji, color = "😐", "orange"
            elif total_score >= 2:
                emoji, color = "😔", "red"
            else:
                emoji, color = "😢", "red"
                
            st.markdown(f"### 🎯 오늘의 감정 점수: **:{color}[{total_score}/10점]** {emoji}")
            
            if date_str in data:
                item = data[date_str]
                st.write("**🎭 세부 감정 분석:**")
                emotion_cols = st.columns(5)
                emotions = [
                    ("😄", "기쁨", item["joy"]),
                    ("😢", "슬픔", item["sadness"]), 
                    ("😡", "분노", item["anger"]),
                    ("😰", "불안", item["anxiety"]),
                    ("😌", "평온", item["calmness"])
                ]
                
                for i, (emoji, name, score) in enumerate(emotions):
                    with emotion_cols[i]:
                        st.metric(f"{emoji} {name}", f"{score}")
                
                if message:
                    st.success(f"💌 **AI의 따뜻한 메시지**\n\n{message}")
        else:
            st.info("💡 일기를 작성하면 AI가 감정을 분석해드려요!")

with tab2:
    st.subheader("📊 나의 감정 통계")
    
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 아직 작성된 일기가 없습니다.\n첫 일기를 써보세요! ✨")
    else:
        average_total_score = calc_average_total_score(items)
        item_count = len(items)
        char_count = calc_char_count(items)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📈 평균 감정점수", f"{average_total_score}점")
            st.metric("✏️ 총 글자수", f"{char_count:,}자")
        with col2:
            st.metric("📚 일기 개수", f"{item_count}개")
            days_active = len(set([item["date"][:7] for item in items]))
            st.metric("📅 활동 월수", f"{days_active}개월")
        
        st.divider()
        
        st.write("🏷️ **자주 사용한 키워드 TOP 10**")
        keyword_counts = calc_keyword_count(items)
        if keyword_counts:
            sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            for i, (keyword, count) in enumerate(sorted_keywords):
                if i < 3:
                    medals = ["🥇", "🥈", "🥉"]
                    st.markdown(f"### {medals[i]} **{keyword}** `{count}회`")
                else:
                    st.markdown(f"**{i+1}.** {keyword} `{count}회`")

with tab3:
    st.subheader("📈 감정 변화 분석")
    
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기가 2개 이상 있어야 그래프를 볼 수 있어요!")
    else:
        st.write("**🎯 감정 점수 변화**")
        total_scores = [{"날짜": item["date"][5:], "점수": item["total_score"]} 
                       for item in items[-14:]]
        st.line_chart(total_scores, x="날짜", y="점수", height=300)
        
        st.write("**🎭 감정별 변화 (최근 2주)**")
        emotion_scores = [{
            "날짜": item["date"][5:],
            "😄기쁨": item["joy"],
            "😌평온": item["calmness"],
            "😰불안": item["anxiety"],
            "😢슬픔": item["sadness"],
            "😡분노": item["anger"],
        } for item in items[-14:]]
        
        st.area_chart(
            emotion_scores, x="날짜",
            y=["😄기쁨", "😌평온", "😰불안", "😢슬픔", "😡분노"],
            height=300
        )
        
        if len(items) >= 7:
            st.divider()
            st.write("**📋 최근 일주일 감정 요약**")
            
            recent_week = items[-7:]
            avg_emotions = {
                "joy": sum(item["joy"] for item in recent_week) / 7,
                "sadness": sum(item["sadness"] for item in recent_week) / 7,
                "anger": sum(item["anger"] for item in recent_week) / 7,
                "anxiety": sum(item["anxiety"] for item in recent_week) / 7,
                "calmness": sum(item["calmness"] for item in recent_week) / 7,
            }
            
            max_emotion = max(avg_emotions, key=avg_emotions.get)
            emotion_names = {
                "joy": "😄 기쁨", "sadness": "😢 슬픔", "anger": "😡 분노",
                "anxiety": "😰 불안", "calmness": "😌 평온"
            }
            
            st.info(f"최근 일주일 동안 **{emotion_names[max_emotion]}**이 가장 높았어요! "
                   f"({avg_emotions[max_emotion]:.1f}점)")

# 하단 안내
st.divider()
st.markdown("### 💝 매일 감정을 기록하며 마음을 돌보세요!")
st.caption("🤖 AI가 당신의 감정을 분석하고 응원 메시지를 보내드려요")
st.caption("☁️ 모든 데이터는 Google Sheets에 안전하게 보관됩니다")

# iOS 홈 화면 추가 안내
if 'show_install_guide' not in st.session_state:
    st.session_state.show_install_guide = True

if st.session_state.show_install_guide:
    with st.expander("📱 아이폰 홈 화면에 추가하기"):
        st.markdown("""
        **앱처럼 사용하는 방법:**
        1. Safari 하단의 공유 버튼 📤 터치
        2. "홈 화면에 추가" 선택  
        3. "추가" 버튼 터치
        4. 홈 화면에서 앱처럼 사용! 🎉
        
        **☁️ 클라우드 저장 장점:**
        - 언제 어디서나 접속 가능
        - 데이터 영구 보관
        - 자동 백업
        """)
        
        if st.button("✅ 확인했어요"):
            st.session_state.show_install_guide = False
            st.rerun()

