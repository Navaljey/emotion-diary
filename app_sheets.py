import json
import os
from datetime import datetime, timedelta
import streamlit as st
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import matplotlib
import networkx as nx
from io import BytesIO
import numpy as np

# 한글 폰트 설정 (matplotlib 백엔드 설정)
matplotlib.use('Agg')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# PWA HTML
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
    .stTabs [data-baseweb="tab"] { height: 3rem; padding: 0.5rem 1rem; }
    .stButton > button { height: 3rem; font-size: 1.1rem; }
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
    
    st.sidebar.markdown("### 🔍 사용 가능한 Gemini 모델")
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                st.sidebar.success(f"✅ {m.name}")
        
        if available_models:
            model_name = available_models[0].replace('models/', '')
            st.sidebar.info(f"📌 사용 중: {model_name}")
            model = genai.GenerativeModel(model_name)
        else:
            st.error("❌ 사용 가능한 Gemini 모델이 없습니다.")
            st.stop()
    except Exception as e:
        st.sidebar.error(f"모델 확인 오류: {e}")
        model = genai.GenerativeModel('gemini-pro')
else:
    st.error("🔑 GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

# Google Sheets 연결
@st.cache_resource
def init_google_sheets():
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        
        SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        try:
            diary_ws = spreadsheet.worksheet("diary_data")
        except:
            diary_ws = spreadsheet.add_worksheet(title="diary_data", rows=1000, cols=20)
            diary_ws.update('A1:K1', [[
                'date', 'content', 'keywords', 'total_score', 
                'joy', 'sadness', 'anger', 'anxiety', 'calmness', 
                'message', 'created_at'
            ]])
        
        try:
            expert_ws = spreadsheet.worksheet("expert_advice")
        except:
            expert_ws = spreadsheet.add_worksheet(title="expert_advice", rows=1000, cols=20)
            expert_ws.update('A1:E1', [['date', 'expert_type', 'advice', 'has_content', 'created_at']])
        
        try:
            reminder_ws = spreadsheet.worksheet("reminders")
        except:
            reminder_ws = spreadsheet.add_worksheet(title="reminders", rows=1000, cols=20)
            reminder_ws.update('A1:D1', [['date', 'reminder_type', 'message', 'is_read']])
        
        return diary_ws, expert_ws, reminder_ws
    except Exception as e:
        st.error(f"❌ Google Sheets 연결 실패: {e}")
        st.stop()

diary_worksheet, expert_worksheet, reminder_worksheet = init_google_sheets()

def load_data_from_sheets():
    try:
        st.sidebar.info("🔄 데이터 로딩 중...")
        records = diary_worksheet.get_all_records()
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
        return {}

def save_data_to_sheets(date_str, item_data):
    try:
        st.info(f"🔄 저장 시도: {date_str}")
        all_values = diary_worksheet.get_all_values()
        st.info(f"📊 현재 시트 행 수: {len(all_values)}")
        
        row_index = None
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) > 0 and row[0] == date_str:
                row_index = idx
                st.info(f"📝 기존 데이터 발견: {row_index}행")
                break
        
        keywords_str = json.dumps(item_data['keywords'], ensure_ascii=False)
        row_data = [
            str(date_str), str(item_data['content']), str(keywords_str), 
            float(item_data['total_score']),
            int(item_data['joy']), int(item_data['sadness']), int(item_data['anger']),
            int(item_data['anxiety']), int(item_data['calmness']), 
            str(item_data['message']),
            datetime.now().isoformat()
        ]
        
        st.info(f"💾 저장할 데이터: {row_data[:3]}...")
        
        if row_index:
            diary_worksheet.update(f'A{row_index}:K{row_index}', [row_data])
            st.success(f"✅ {row_index}행 업데이트 완료!")
        else:
            diary_worksheet.append_row(row_data)
            st.success(f"✅ 새 행 추가 완료!")
        
        import time
        time.sleep(1)
        updated_values = diary_worksheet.get_all_values()
        st.success(f"🎉 저장 후 시트 행 수: {len(updated_values)}")
        
        return True
    except Exception as e:
        st.error(f"❌ 저장 오류: {e}")
        import traceback
        st.error(f"상세:\n```\n{traceback.format_exc()}\n```")
        return False

def delete_data_from_sheets(date_str):
    try:
        all_values = diary_worksheet.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if row[0] == date_str:
                diary_worksheet.delete_rows(idx)
                return True
        return False
    except Exception as e:
        st.error(f"삭제 오류: {e}")
        return False

def get_latest_data():
    data = load_data_from_sheets()
    items = sorted(data.values(), key=lambda x: x["date"])[-30:]
    return data, items

def save_expert_advice_to_sheets(date_str, expert_type, advice, has_content):
    try:
        all_values = expert_worksheet.get_all_values()
        row_index = None
        
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) >= 2 and row[0] == date_str and row[1] == expert_type:
                row_index = idx
                break
        
        row_data = [str(date_str), str(expert_type), str(advice), str(has_content), datetime.now().isoformat()]
        
        if row_index:
            expert_worksheet.update(f'A{row_index}:E{row_index}', [row_data])
        else:
            expert_worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        st.error(f"조언 저장 오류: {e}")
        return False

def load_expert_advice_from_sheets(date_str):
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
        return {}

def save_reminder(reminder_type, message):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        row_data = [today, reminder_type, message, 'False']
        reminder_worksheet.append_row(row_data)
        return True
    except:
        return False

def load_unread_reminders():
    try:
        records = reminder_worksheet.get_all_records()
        unread = []
        for record in records:
            if record.get('is_read') == 'False' or record.get('is_read') == False:
                unread.append(record)
        return unread
    except:
        return []

def mark_reminder_as_read(date, reminder_type):
    try:
        all_values = reminder_worksheet.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if row[0] == date and row[1] == reminder_type:
                reminder_worksheet.update(f'D{idx}', [['True']])
                break
        return True
    except:
        return False

def check_and_create_reminders(items):
    if not items:
        return
    
    today = datetime.now().date()
    
    # 마지막 일기 날짜 확인
    last_diary_date = datetime.strptime(items[-1]['date'], '%Y-%m-%d').date()
    days_since_last = (today - last_diary_date).days
    
    # 3일 이상 일기를 안 썼으면 알림
    if days_since_last >= 3:
        message = f"💭 마지막 일기를 쓴 지 {days_since_last}일이 지났습니다. 오늘의 감정을 기록해보세요!"
        save_reminder("일기_작성_독려", message)
    
    # 주간 분석 알림 (매주 일요일)
    if today.weekday() == 6:  # 일요일
        message = "📊 이번 주 감정을 돌아볼 시간입니다. 전문가 조언을 받아보세요!"
        save_reminder("주간_분석", message)

def create_emotion_flow_chart(items):
    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        recent_items = items[-14:] if len(items) >= 14 else items
        dates = [item['date'][-5:] for item in recent_items]
        joy = [item['joy'] for item in recent_items]
        sadness = [item['sadness'] for item in recent_items]
        anger = [item['anger'] for item in recent_items]
        anxiety = [item['anxiety'] for item in recent_items]
        calmness = [item['calmness'] for item in recent_items]
        
        ax.plot(dates, joy, marker='o', label='Joy', color='#FFD700', linewidth=2)
        ax.plot(dates, sadness, marker='o', label='Sadness', color='#4169E1', linewidth=2)
        ax.plot(dates, anger, marker='o', label='Anger', color='#DC143C', linewidth=2)
        ax.plot(dates, anxiety, marker='o', label='Anxiety', color='#FF8C00', linewidth=2)
        ax.plot(dates, calmness, marker='o', label='Calm', color='#32CD32', linewidth=2)
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Emotion Score', fontsize=12)
        ax.set_title('Emotion Flow Analysis (Recent 2 Weeks)', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    except Exception as e:
        st.error(f"그래프 생성 오류: {e}")
        return None

def create_emotion_network(items):
    try:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        recent_items = items[-30:] if len(items) >= 30 else items
        
        emotions = {
            'Joy': [item['joy'] for item in recent_items],
            'Sadness': [item['sadness'] for item in recent_items],
            'Anger': [item['anger'] for item in recent_items],
            'Anxiety': [item['anxiety'] for item in recent_items],
            'Calm': [item['calmness'] for item in recent_items]
        }
        
        G = nx.Graph()
        emotion_names = list(emotions.keys())
        for emotion in emotion_names:
            G.add_node(emotion)
        
        for i, e1 in enumerate(emotion_names):
            for j, e2 in enumerate(emotion_names):
                if i < j:
                    corr = np.corrcoef(emotions[e1], emotions[e2])[0, 1]
                    if abs(corr) > 0.3:
                        G.add_edge(e1, e2, weight=abs(corr))
        
        pos = nx.spring_layout(G, k=2, iterations=50)
        node_colors = ['#FFD700', '#4169E1', '#DC143C', '#FF8C00', '#32CD32']
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000, alpha=0.9, ax=ax)
        
        edges = G.edges()
        weights = [G[u][v]['weight'] for u, v in edges]
        nx.draw_networkx_edges(G, pos, width=[w*5 for w in weights], alpha=0.5, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=14, font_weight='bold', ax=ax)
        
        ax.set_title('Emotion Correlation Network', fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    except Exception as e:
        st.error(f"네트워크 그래프 오류: {e}")
        return None

def create_goal_flowchart(items):
    try:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        recent_items = items[-14:] if len(items) >= 14 else items
        dates = [item['date'][-5:] for item in recent_items]
        scores = [item['total_score'] for item in recent_items]
        
        ax.plot(dates, scores, marker='o', color='#1E90FF', linewidth=3, 
                markersize=10, label='Motivation/Energy Level')
        
        avg_score = sum(scores) / len(scores)
        ax.axhline(y=avg_score, color='r', linestyle='--', linewidth=2, 
                   alpha=0.7, label=f'Average: {avg_score:.1f}')
        ax.axhline(y=8, color='g', linestyle='--', linewidth=2, 
                   alpha=0.5, label='Target: 8.0')
        
        ax.fill_between(range(len(dates)), scores, avg_score, 
                        where=[s >= avg_score for s in scores],
                        alpha=0.3, color='green', label='Rising')
        ax.fill_between(range(len(dates)), scores, avg_score,
                        where=[s < avg_score for s in scores],
                        alpha=0.3, color='red', label='Falling')
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Motivation Level', fontsize=12)
        ax.set_title('Goal Achievement Motivation Analysis', fontsize=14, fontweight='bold')
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
    except Exception as e:
        st.error(f"플로우차트 오류: {e}")
        return None

def create_metaphor_prompt(items):
    recent_items = items[-7:] if len(items) >= 7 else items
    emotions_summary = {'joy': 0, 'sadness': 0, 'anger': 0, 'anxiety': 0, 'calmness': 0}
    
    for item in recent_items:
        for emotion in emotions_summary:
            emotions_summary[emotion] += item[emotion]
    
    dominant_emotion = max(emotions_summary, key=emotions_summary.get)
    
    metaphors = {
        'joy': '☀️ Bright sunshine, blooming flowers, soaring birds',
        'sadness': '🌧️ Rainy sky, calm lake, falling leaves',
        'anger': '🔥 Burning flames, storm, rough waves',
        'anxiety': '🌀 Dark maze, tangled threads, flickering flame',
        'calmness': '🌊 Calm sea, peaceful forest, sky above clouds'
    }
    
    return f"""
🎨 **Your Emotional Metaphor:**

Dominant Emotion: {dominant_emotion.upper()}
Symbol: {metaphors[dominant_emotion]}

This image represents the symbolic expression of emotions from your unconscious.
Through images like {metaphors[dominant_emotion]}, 
you can visualize and understand your inner feelings.
"""

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
    except Exception as e:
        st.error(f"❌ 분석 오류: {e}")
    
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
    except:
        pass
    
    return "오늘도 일기를 써주셔서 감사해요! 😊"

def get_expert_advice(expert_type, diary_data):
    sorted_diaries = sorted(diary_data.values(), key=lambda x: x['date'])
    recent_diaries = sorted_diaries[-30:]
    
    diary_summary = []
    for diary in recent_diaries:
        summary = f"날짜: {diary['date']}, 내용: {diary['content'][:100]}..., 감정점수: {diary['total_score']}"
        diary_summary.append(summary)
    
    diary_text = "\n".join(diary_summary)
    
    expert_prompts = {
        "심리상담사": f"당신은 경험 많은 심리상담사입니다.\n\n{diary_text}\n\n위 일기들을 분석하여 감정 패턴, 스트레스 요인, 심리적 건강 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}",
        "재정관리사": f"당신은 전문 재정관리사입니다.\n\n{diary_text}\n\n재정 관련 내용을 찾아 소비 패턴, 재정 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}",
        "변호사": f"당신은 경험 많은 변호사입니다.\n\n{diary_text}\n\n법적 문제를 찾아 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}",
        "의사": f"당신은 종합병원 의사입니다.\n\n{diary_text}\n\n건강 관련 내용을 찾아 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}",
        "피부관리사": f"당신은 전문 피부관리사입니다.\n\n{diary_text}\n\n피부 관련 내용을 찾아 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}",
        "피트니스 트레이너": f"당신은 피트니스 트레이너입니다.\n\n{diary_text}\n\n운동 관련 내용을 찾아 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}",
        "창업 벤처투자자": f"당신은 성공한 창업가입니다.\n\n{diary_text}\n\n비즈니스 관련 내용을 찾아 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}",
        "예술치료사": f"당신은 예술치료사입니다.\n\n{diary_text}\n\n창의적 표현 활동을 제안하는 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true}}",
        "임상심리사": f"당신은 임상심리사입니다.\n\n{diary_text}\n\n정신건강 상태를 평가하는 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true}}",
        "조직심리 전문가": f"당신은 조직심리 전문가입니다.\n\n{diary_text}\n\n직장 관련 내용을 찾아 조언을 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}"
    }
    
    prompt = expert_prompts.get(expert_type, "")
    
    try:
        with st.spinner(f'🤖 {expert_type} 분석 중...'):
            response_text = gemini_chat(prompt)
            if response_text:
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

def compare_periods(items):
    """기간별 비교 분석"""
    if len(items) < 14:
        return None
    
    # 최근 1주와 이전 1주 비교
    recent_week = items[-7:]
    prev_week = items[-14:-7]
    
    def calc_avg(period):
        return {
            'joy': sum(i['joy'] for i in period) / len(period),
            'sadness': sum(i['sadness'] for i in period) / len(period),
            'anger': sum(i['anger'] for i in period) / len(period),
            'anxiety': sum(i['anxiety'] for i in period) / len(period),
            'calmness': sum(i['calmness'] for i in period) / len(period),
            'total': sum(i['total_score'] for i in period) / len(period)
        }
    
    recent_avg = calc_avg(recent_week)
    prev_avg = calc_avg(prev_week)
    
    comparison = {}
    for key in recent_avg:
        diff = recent_avg[key] - prev_avg[key]
        comparison[key] = {
            'recent': recent_avg[key],
            'previous': prev_avg[key],
            'diff': diff,
            'trend': '상승' if diff > 0.5 else ('하락' if diff < -0.5 else '유지')
        }
    
    return comparison

# 메인 화면
st.title("📱 감정 일기")
st.caption("AI가 분석하는 나만의 감정 기록 ☁️")

# 알림 확인
unread_reminders = load_unread_reminders()
if unread_reminders:
    st.warning(f"🔔 {len(unread_reminders)}개의 새 알림이 있습니다!")
    with st.expander("알림 보기", expanded=True):
        for reminder in unread_reminders:
            st.info(f"📅 {reminder['date']}: {reminder['message']}")
            if st.button(f"확인 완료", key=f"read_{reminder['date']}_{reminder['reminder_type']}"):
                mark_reminder_as_read(reminder['date'], reminder['reminder_type'])
                st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["✍️ 쓰기", "📊 통계", "📈 그래프", "👨‍⚕️ 전문가 조언", "🔔 알림/비교"])

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
    
    content = st.text_area("📝 오늘 하루는 어땠나요?", default_content, height=200,
                           placeholder="자유롭게 마음을 적어보세요...")
    
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
    st.caption("일기 내용을 시간순으로 분석하여 전문가 조언을 제공합니다")
    
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기를 작성하면 전문가 조언을 받을 수 있습니다.")
    else:
        st.success(f"📊 최근 {len(items)}개의 일기를 분석합니다")
        
        st.markdown("### 📅 조언 확인 날짜 선택")
        available_dates = sorted([item['date'] for item in items], reverse=True)
        selected_advice_date = st.selectbox("날짜를 선택하세요", options=available_dates, index=0)
        
        saved_advice = load_expert_advice_from_sheets(selected_advice_date)
        if saved_advice:
            st.info(f"💾 {selected_advice_date}에 저장된 조언: {len(saved_advice)}개")
        
        st.divider()
        
        expert_tabs = st.tabs([
            "🧠 심리상담", "💰 재정", "⚖️ 변호사", "🏥 의사", "✨ 피부",
            "💪 피트니스", "🚀 창업", "🎨 예술", "🧬 임상", "👔 조직"
        ])
        
        experts_info = [
            ("심리상담사", "🧠", True),
            ("재정관리사", "💰", False),
            ("변호사", "⚖️", False),
            ("의사", "🏥", False),
            ("피부관리사", "✨", False),
            ("피트니스 트레이너", "💪", False),
            ("창업 벤처투자자", "🚀", True),
            ("예술치료사", "🎨", False),
            ("임상심리사", "🧬", True),
            ("조직심리 전문가", "👔", False)
        ]
        
        for idx, (expert_name, icon, show_chart) in enumerate(experts_info):
            with expert_tabs[idx]:
                st.markdown(f"### {icon} {expert_name}")
                
                if expert_name in saved_advice:
                    st.success(f"📋 저장된 조언 ({saved_advice[expert_name]['created_at'][:10]})")
                    st.markdown(saved_advice[expert_name]["advice"])
                    st.divider()
                
                if st.button(f"💬 {expert_name} 조언 받기", key=f"btn_{expert_name}", use_container_width=True):
                    if show_chart and len(items) >= 2:
                        if expert_name in ["심리상담사", "임상심리사"]:
                            flow_chart = create_emotion_flow_chart(items)
                            if flow_chart:
                                st.image(flow_chart, caption="Emotion Flow", use_container_width=True)
                            network_chart = create_emotion_network(items)
                            if network_chart:
                                st.image(network_chart, caption="Emotion Network", use_container_width=True)
                        elif expert_name == "창업 벤처투자자":
                            goal_chart = create_goal_flowchart(items)
                            if goal_chart:
                                st.image(goal_chart, caption="Goal Flow", use_container_width=True)
                    
                    if expert_name == "예술치료사":
                        metaphor = create_metaphor_prompt(items)
                        st.info(metaphor)
                    
                    result = get_expert_advice(expert_name, data)
                    if result.get("has_content"):
                        st.success(f"**{expert_name}의 조언:**")
                        st.markdown(result["advice"])
                        save_expert_advice_to_sheets(selected_advice_date, expert_name, 
                                                    result["advice"], result["has_content"])
                        st.success("💾 조언이 저장되었습니다")
                    else:
                        st.info(result["advice"])
        
        st.divider()
        st.warning("⚠️ **주의**: AI 조언은 참고용입니다. 전문가 상담이 필요한 경우 반드시 전문의와 상담하세요.")

with tab5:
    st.subheader("🔔 알림 관리 & 📊 기간별 비교")
    data, items = get_latest_data()
    
    st.markdown("### 🔔 알림 설정")
    
    # 알림 체크 및 생성
    if items:
        check_and_create_reminders(items)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 일기 작성 독려 알림 생성", use_container_width=True):
            save_reminder("수동_독려", "💭 오늘의 감정을 기록해보세요!")
            st.success("알림이 생성되었습니다!")
            st.rerun()
    
    with col2:
        if st.button("📊 주간 분석 알림 생성", use_container_width=True):
            save_reminder("수동_주간분석", "📊 이번 주 감정을 돌아보세요!")
            st.success("알림이 생성되었습니다!")
            st.rerun()
    
    st.divider()
    st.markdown("### 📊 기간별 비교 분석")
    
    if len(items) >= 14:
        comparison = compare_periods(items)
        
        if comparison:
            st.write("**📈 최근 1주 vs 이전 1주**")
            
            for emotion, data_cmp in comparison.items():
                if emotion == 'total':
                    continue
                
                emotion_names = {
                    'joy': '😄 기쁨',
                    'sadness': '😢 슬픔',
                    'anger': '😡 분노',
                    'anxiety': '😰 불안',
                    'calmness': '😌 평온'
                }
                
                trend_icon = "📈" if data_cmp['trend'] == '상승' else ("📉" if data_cmp['trend'] == '하락' else "➡️")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(emotion_names.get(emotion, emotion), 
                             f"{data_cmp['recent']:.1f}",
                             f"{data_cmp['diff']:+.1f}")
                with col2:
                    st.write(f"이전 주: {data_cmp['previous']:.1f}")
                with col3:
                    st.write(f"{trend_icon} {data_cmp['trend']}")
            
            st.divider()
            
            # 종합 분석
            total_trend = comparison['total']['trend']
            if total_trend == '상승':
                st.success(f"🎉 종합 감정 점수가 상승했습니다! ({comparison['total']['diff']:+.1f}점)")
            elif total_trend == '하락':
                st.warning(f"😔 종합 감정 점수가 하락했습니다. ({comparison['total']['diff']:+.1f}점)")
            else:
                st.info(f"➡️ 종합 감정 점수가 유지되고 있습니다.")
    else:
        st.info("📝 비교 분석을 위해서는 최소 14개의 일기가 필요합니다.")

st.divider()
st.markdown("### 💝 매일 감정을 기록하며 마음을 돌보세요!")
st.caption("🤖 AI 분석 | ☁️ 클라우드 저장 | 🔔 알림 기능")

