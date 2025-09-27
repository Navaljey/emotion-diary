import json
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai

# PWA를 위한 HTML 코드 - 수정된 버전
pwa_html = """
<link rel="manifest" href="data:application/json;charset=utf-8,%7B%22name%22%3A%22%EA%B0%90%EC%A0%95%20%EC%9D%BC%EA%B8%B0%22%2C%22short_name%22%3A%22%EA%B0%90%EC%A0%95%EC%9D%BC%EA%B8%B0%22%2C%22description%22%3A%22AI%EA%B0%80%20%EB%B6%84%EC%84%9D%ED%95%98%EB%8A%94%20%EA%B0%90%EC%A0%95%20%EC%9D%BC%EA%B8%B0%20%EC%95%B1%22%2C%22start_url%22%3A%22%2F%22%2C%22display%22%3A%22standalone%22%2C%22background_color%22%3A%22%23ffffff%22%2C%22theme_color%22%3A%22%23ff6b6b%22%2C%22icons%22%3A%5B%7B%22src%22%3A%22data%3Aimage%2Fsvg%2Bxml%3Bcharset%3Dutf-8%2C%253Csvg%2520xmlns%253D%2522http%253A%252F%252Fwww.w3.org%252F2000%252Fsvg%2522%2520viewBox%253D%25220%25200%2520100%2520100%2522%253E%253Ctext%2520y%253D%2522.9em%2522%2520font-size%253D%252290%2522%253E%25E2%259C%258D%25EF%25B8%258F%253C%252Ftext%253E%253C%252Fsvg%253E%22%2C%22sizes%22%3A%22192x192%22%2C%22type%22%3A%22image%2Fsvg%2Bxml%22%7D%5D%7D">

<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/sw.js');
  });
}
</script>

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
    
    /* 탭 버튼 크기 조정 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0.5rem 1rem;
    }
    
    /* 버튼 크기 확대 */
    .stButton > button {
        height: 3rem;
        font-size: 1.1rem;
    }
    
    /* 메트릭 카드 스타일 */
    [data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e1e5eb;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
}

/* iOS Safari 전용 스타일 */
@supports (-webkit-touch-callout: none) {
    .stApp {
        -webkit-user-select: none;
        -webkit-tap-highlight-color: transparent;
    }
}
</style>
"""

# Streamlit 페이지 설정 - 모바일 최적화
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

# PWA HTML 삽입
st.markdown(pwa_html, unsafe_allow_html=True)

_ = load_dotenv(find_dotenv())

# Google AI Studio API 키 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("🔑 GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    st.stop()

# 파일명 상수 정의 - 절대경로 사용
FILENAME = os.path.abspath("emotion_diary_data.json")

def load_data(filename):
    """데이터 로드 함수 - 에러 처리 강화"""
    data = {}
    try:
        # 파일이 존재하는지 먼저 확인
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as file:
                content = file.read().strip()
                if content:  # 파일이 비어있지 않은 경우만
                    data = json.loads(content)
                else:
                    print(f"파일이 비어있음: {filename}")
        else:
            print(f"파일이 존재하지 않음: {filename}")
    except json.JSONDecodeError as e:
        print(f"JSON 디코드 에러: {e}")
        # 백업 파일 확인
        backup_filename = filename + ".backup"
        if os.path.exists(backup_filename):
            try:
                with open(backup_filename, "r", encoding="utf-8") as file:
                    data = json.load(file)
                print("백업 파일에서 데이터 복구 완료")
            except:
                print("백업 파일도 손상됨")
    except Exception as e:
        print(f"데이터 로드 에러: {e}")
    
    return data

def save_data(filename, data):
    """데이터 저장 함수 - 백업 기능 추가"""
    try:
        # 기존 파일이 있으면 백업 생성
        if os.path.exists(filename):
            backup_filename = filename + ".backup"
            import shutil
            shutil.copy2(filename, backup_filename)
        
        # 데이터 저장
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        
        # 저장 확인
        if os.path.exists(filename):
            print(f"데이터 저장 완료: {filename}")
        else:
            print(f"데이터 저장 실패: {filename}")
            
    except Exception as e:
        print(f"데이터 저장 에러: {e}")
        st.error(f"데이터 저장 중 오류가 발생했습니다: {e}")

def get_latest_data():
    """최신 데이터를 로드하는 함수 - 디버깅 정보 추가"""
    data = load_data(FILENAME)
    
    # 디버깅 정보
    if data:
        print(f"로드된 일기 개수: {len(data)}")
        dates = sorted(data.keys())
        if dates:
            print(f"가장 오래된 일기: {dates[0]}")
            print(f"가장 최근 일기: {dates[-1]}")
    else:
        print("로드된 데이터가 없음")
    
    items = []
    for item in data.values():
        items.append(item)
    items.sort(key=lambda x: x["date"])
    items = items[-30:]  # 최근 30개만
    
    return data, items

def calc_average_total_score(items):
    if len(items) == 0:
        return 0
    total_score_sum = 0
    for item in items:
        total_score_sum += item["total_score"]
    return round(total_score_sum / len(items), 2)

def calc_char_count(items):
    char_count = 0
    for item in items:
        char_count += len(item["content"])
    return char_count

def calc_keyword_count(items):
    keyword_count = {}
    for item in items:
        for keyword in item["keywords"]:
            if keyword in keyword_count:
                keyword_count[keyword] += 1
            else:
                keyword_count[keyword] = 1
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
    ---
    {{
      "keywords": ["축구", "슛", "친구", "즐거웠다", "신난다"],
      "joy": 8,
      "sadness": 0,
      "anger": 0,
      "anxiety": 0,
      "calmness": 1
    }}
    
    반드시 유효한 JSON 형식으로만 답변해주세요. 다른 텍스트는 포함하지 마세요.
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
        print(f"감정 분석 오류: {e}")
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
    - 최근 감정 상태의 변화를 알려 주는 내용 (만약 최근 데이터가 없다면 생략합니다)
    - 오늘의 일기에 대해 위로와 공감하는 내용
    - 계속 일기를 쓸 수 있도록 응원하는 내용
    메시지의 스타일은 다음과 같이 해주세요.
    - 적당한 이모지를 섞어 친근한 느낌
    
    다음은 답변 JSON형식의 예시입니다.
    ---
    {{ "message": "최근 많이 슬펐던 것 같은데 오늘은 기분이 나아져서 다행이에요 😄 친구들과 함께 즐거운 시간 보내셨나요? 내일 숙제가 걱정이지만 잘 해낼 거예요. 어떤 하루를 보내고 돌아 오실지 벌써부터 궁금해지는 걸요! 💪" }}
    
    반드시 유효한 JSON 형식으로만 답변해주세요. 다른 텍스트는 포함하지 마세요.
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
            return "오늘도 일기를 써주셔서 감사해요! 😊 매일 자신의 마음을 돌아보는 시간을 갖는 것은 정말 소중한 일이에요. 내일도 좋은 하루 되시길 바라요! ✨"
    except Exception as e:
        print(f"메시지 생성 오류: {e}")
        return "오늘도 일기를 써주셔서 감사해요! 😊 매일 자신의 마음을 돌아보는 시간을 갖는 것은 정말 소중한 일이에요. 내일도 좋은 하루 되시길 바라요! ✨"

def calc_total_score(item):
    score = (
        2 * item["joy"] + 1.5 * item["calmness"] - 
        2 * item["sadness"] - 1.5 * item["anxiety"] - 1.5 * item["anger"] + 50
    )
    return round(score / 8.5, 2)

# 메인 화면 구성
st.title("📱 감정 일기")
st.caption("AI가 분석하는 나만의 감정 기록")

# 디버깅 정보 (개발 중에만 표시)
if st.sidebar.checkbox("🔧 디버깅 정보"):
    st.sidebar.write(f"**파일 경로:** {FILENAME}")
    st.sidebar.write(f"**파일 존재:** {os.path.exists(FILENAME)}")
    if os.path.exists(FILENAME):
        file_size = os.path.getsize(FILENAME)
        st.sidebar.write(f"**파일 크기:** {file_size} bytes")
        file_time = os.path.getmtime(FILENAME)
        st.sidebar.write(f"**최종 수정:** {datetime.fromtimestamp(file_time)}")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["✍️ 쓰기", "📊 통계", "📈 그래프"])

with tab1:
    st.subheader("오늘의 마음")
    
    # 최신 데이터 로드
    data, items = get_latest_data()
    
    # 세션 상태 초기화
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
    
    # 데이터 로드 상태 표시
    if data:
        st.success(f"✅ {len(data)}개의 일기가 로드되었습니다")
    else:
        st.info("📝 저장된 일기가 없습니다. 첫 일기를 써보세요!")
    
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
        # 일기가 존재할 때만 삭제 버튼 표시하고, 확인 후 삭제
        if diary_exists:
            delete_clicked = st.button("🗑️", help="일기 삭제하기")
            if delete_clicked:
                # 삭제 확인을 위한 세션 상태
                st.session_state.confirm_delete = date_str  # 삭제할 날짜를 저장
                st.rerun()
        else:
            # 일기가 없을 때는 내용만 지우는 버튼
            if st.button("🗑️", help="내용 지우기"):
                st.rerun()
    
    # 삭제 확인 다이얼로그
    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        delete_date = st.session_state.confirm_delete
        st.warning(f"⚠️ {delete_date} 일기를 정말로 삭제하시겠습니까?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ 예, 삭제합니다", type="primary", key="confirm_yes"):
                # JSON 파일에서 해당 날짜 데이터 삭제
                current_data = load_data(FILENAME)  # 최신 데이터 다시 로드
                if delete_date in current_data:
                    del current_data[delete_date]
                    save_data(FILENAME, current_data)
                    st.success("🗑️ 일기가 삭제되었습니다.")
                # 세션 상태 정리
                del st.session_state.confirm_delete
                st.rerun()
        with col_no:
            if st.button("❌ 아니오, 취소", key="confirm_no"):
                # 세션 상태 정리
                del st.session_state.confirm_delete
                st.rerun()
        
        # 확인 대화상자가 표시된 상태에서는 저장 기능 비활성화
        save_clicked = False
    
    if save_clicked:
        if content.strip():
            with st.spinner('🤖 AI가 감정을 분석 중...'):
                # 최신 데이터로 저장 작업 수행
                current_data = load_data(FILENAME)
                analyzed = sentiment_analysis(content)
                
                # 최신 items로 recent_data 생성
                current_items = []
                for item in current_data.values():
                    current_items.append(item)
                current_items.sort(key=lambda x: x["date"])
                current_items = current_items[-7:]  # 최근 7개
                
                today_data = {
                    "date": date_str,
                    "keywords": analyzed["keywords"],
                    "joy": analyzed["joy"], "sadness": analyzed["sadness"],
                    "anger": analyzed["anger"], "anxiety": analyzed["anxiety"],
                    "calmness": analyzed["calmness"],
                }
                recent_data = []
                for item in current_items:
                    recent_data.append({
                        "date": item["date"], "keywords": item["keywords"],
                        "joy": item["joy"], "sadness": item["sadness"],
                        "anger": item["anger"], "anxiety": item["anxiety"],
                        "calmness": item["calmness"],
                    })
                message = generate_message(today_data, recent_data)
                new_item = {
                    "date": date_str, "content": content, "keywords": analyzed["keywords"],
                    "total_score": calc_total_score(analyzed),
                    "joy": analyzed["joy"], "sadness": analyzed["sadness"],
                    "anger": analyzed["anger"], "anxiety": analyzed["anxiety"],
                    "calmness": analyzed["calmness"], "message": message,
                }
                current_data[date_str] = new_item
                save_data(FILENAME, current_data)
                st.success("✅ 일기가 저장되었습니다!")
                st.balloons()
                st.rerun()
        else:
            st.warning("⚠️ 일기 내용을 입력해주세요!")
    
    # 결과 표시 (삭제 확인 대화상자가 없을 때만)
    if 'confirm_delete' not in st.session_state:
        st.divider()
        
        if total_score is not None:
            # 점수에 따른 이모지와 색상
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
            
            # 감정 분석 결과
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
                
                # AI 메시지
                if message:
                    st.success(f"💌 **AI의 따뜻한 메시지**\n\n{message}")
        else:
            st.info("💡 일기를 작성하면 AI가 감정을 분석해드려요!")

with tab2:
    st.subheader("📊 나의 감정 통계")
    
    # 최신 데이터 로드
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 아직 작성된 일기가 없습니다.\n첫 일기를 써보세요! ✨")
    else:
        # 주요 통계
        average_total_score = calc_average_total_score(items)
        item_count = len(items)
        char_count = calc_char_count(items)
        
        # 통계 카드들
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📈 평균 감정점수", f"{average_total_score}점")
            st.metric("✏️ 총 글자수", f"{char_count:,}자")
        with col2:
            st.metric("📚 일기 개수", f"{item_count}개")
            days_active = len(set([item["date"][:7] for item in items]))  # 활동한 월 수
            st.metric("📅 활동 월수", f"{days_active}개월")
        
        st.divider()
        
        # 키워드 클라우드
        st.write("🏷️ **자주 사용한 키워드 TOP 10**")
        keyword_counts = calc_keyword_count(items)
        if keyword_counts:
            sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # 키워드를 크기별로 표시
            for i, (keyword, count) in enumerate(sorted_keywords):
                size = max(16 - i, 12)  # 순위가 높을수록 큰 글씨
                if i < 3:  # 상위 3개는 메달 이모지
                    medals = ["🥇", "🥈", "🥉"]
                    st.markdown(f"### {medals[i]} **{keyword}** `{count}회`")
                else:
                    st.markdown(f"**{i+1}.** {keyword} `{count}회`")

with tab3:
    st.subheader("📈 감정 변화 분석")
    
    # 최신 데이터 로드
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기가 2개 이상 있어야 그래프를 볼 수 있어요!")
    else:
        # 감정 점수 트렌드
        st.write("**🎯 감정 점수 변화**")
        total_scores = []
        for item in items[-14:]:  # 최근 14개만
            total_scores.append({
                "날짜": item["date"][5:],
                "점수": item["total_score"],
            })
        st.line_chart(total_scores, x="날짜", y="점수", height=300)
        
        # 감정별 분석
        st.write("**🎭 감정별 변화 (최근 2주)**")
        emotion_scores = []
        for item in items[-14:]:
            emotion_scores.append({
                "날짜": item["date"][5:],
                "😄기쁨": item["joy"],
                "😌평온": item["calmness"],
                "😰불안": item["anxiety"],
                "😢슬픔": item["sadness"],
                "😡분노": item["anger"],
            })
        st.area_chart(
            emotion_scores, x="날짜",
            y=["😄기쁨", "😌평온", "😰불안", "😢슬픔", "😡분노"],
            height=300
        )
        
        # 감정 요약
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
            
            # 가장 높은 감정
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

# iOS에서 홈 화면 추가 안내 (첫 방문시에만)
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
        """)
        
        if st.button("✅ 확인했어요"):
            st.session_state.show_install_guide = False
            st.rerun()
