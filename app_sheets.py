import json
import os
from datetime import datetime
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
import requests
from PIL import Image
import base64

# 한글 폰트 설정
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
    .stTabs [data-baseweb="tab"] { height: 3rem; padding: 0.5rem 1rem; font-size: 0.9rem; }
    .stButton > button { height: 3rem; font-size: 1.1rem; }
    [data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e1e5eb;
        padding: 0.8rem;
        border-radius: 0.5rem;
        margin: 0.3rem 0;
    }
    .stMetric { font-size: 0.9rem; }
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

# API 키 설정 (Streamlit Cloud 우선, 로컬 환경변수 대체)
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    NAVER_CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET", "")
    HUGGINGFACE_API_KEY = st.secrets.get("HUGGINGFACE_API_KEY", "")
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
    HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")

# Gemini 설정
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        if available_models:
            model_name = available_models[0].replace('models/', '')
            model = genai.GenerativeModel(model_name)
        else:
            model = genai.GenerativeModel('gemini-pro')
    except:
        model = genai.GenerativeModel('gemini-pro')
else:
    st.error("🔑 GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

CLOVA_ENABLED = bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET)
HUGGINGFACE_ENABLED = bool(HUGGINGFACE_API_KEY)

# Hugging Face 설정 - 여러 모델 대안 제공
HUGGINGFACE_MODELS = [
    "black-forest-labs/FLUX.1-schnell",  # 가장 최신, 빠름
    "runwayml/stable-diffusion-v1-5",  
    "stabilityai/stable-diffusion-xl-base-1.0",
    "prompthero/openjourney",  # 무료 티어에서 작동 가능
]

# 대체 API (Pollinations.ai - 완전 무료, API 키 불필요)
POLLINATIONS_API_URL = "https://image.pollinations.ai/prompt/"

# Google Sheets 연결
@st.cache_resource
def init_google_sheets():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        
        SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        worksheets = {
            "diary_data": ['date', 'content', 'keywords', 'total_score', 'joy', 'sadness', 'anger', 'anxiety', 'calmness', 'message', 'created_at'],
            "expert_advice": ['date', 'expert_type', 'advice', 'has_content', 'created_at'],
            "metaphor_images": ['date', 'image_url', 'prompt', 'created_at']
        }
        
        sheets = {}
        for name, headers in worksheets.items():
            try:
                sheets[name] = spreadsheet.worksheet(name)
            except:
                ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
                ws.update(f'A1:{chr(65+len(headers)-1)}1', [headers])
                sheets[name] = ws
        
        return sheets["diary_data"], sheets["expert_advice"], sheets["metaphor_images"]
    except Exception as e:
        st.error(f"❌ Google Sheets 연결 실패: {e}")
        st.stop()

diary_worksheet, expert_worksheet, metaphor_worksheet = init_google_sheets()

# 네이버 클로버 음성인식
def clova_speech_to_text(audio_file):
    try:
        url = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor"
        headers = {
            "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
            "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET,
            "Content-Type": "application/octet-stream"
        }
        audio_data = audio_file.getvalue()
        response = requests.post(url, headers=headers, data=audio_data)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('text', "❌ 텍스트를 찾을 수 없습니다.")
        else:
            error_msg = response.json().get('errorMessage', '알 수 없는 오류')
            return f"❌ API 오류 ({response.status_code}): {error_msg}"
    except Exception as e:
        return f"❌ 오류: {str(e)}"

# Pollinations.ai 이미지 생성 (완전 무료, API 키 불필요)
def generate_image_with_pollinations(prompt):
    """
    Pollinations.ai로 이미지 생성 (완전 무료, 빠름)
    """
    try:
        # URL 인코딩
        import urllib.parse
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Pollinations.ai API 호출
        image_url = f"{POLLINATIONS_API_URL}{encoded_prompt}?width=512&height=512&nologo=true&enhance=true"
        
        response = requests.get(image_url, timeout=30)
        
        if response.status_code == 200:
            # 이미지를 PIL로 열기
            image = Image.open(BytesIO(response.content))
            
            # base64로 변환
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return img_base64, None
        else:
            return None, f"❌ Pollinations API 오류: HTTP {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Pollinations 오류: {str(e)}"

# Hugging Face 이미지 생성 (디버깅 강화)
def generate_image_with_huggingface(prompt, negative_prompt="", debug_mode=False):
    """
    Hugging Face Stable Diffusion으로 이미지 생성 (자동 폴백)
    """
    if not HUGGINGFACE_ENABLED:
        return None, "Hugging Face API 키가 설정되지 않았습니다."
    
    debug_info = []
    
    # 여러 모델 시도
    for model_idx, model_name in enumerate(HUGGINGFACE_MODELS):
        api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        
        if debug_mode:
            debug_info.append(f"시도 중: {model_name}")
        
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
            }
        }
        
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if debug_mode:
                debug_info.append(f"  → 응답 코드: {response.status_code}")
                debug_info.append(f"  → Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            # 응답 상태 확인
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                
                # 이미지 데이터인 경우
                if 'image' in content_type or len(response.content) > 1000:
                    try:
                        image = Image.open(BytesIO(response.content))
                        buffered = BytesIO()
                        image.save(buffered, format="PNG")
                        img_base64 = base64.b64encode(buffered.getvalue()).decode()
                        
                        if debug_mode:
                            debug_info.append(f"  ✅ 성공!")
                            return img_base64, "\n".join(debug_info)
                        
                        if model_idx > 0:
                            st.info(f"✅ 대체 모델 사용: {model_name}")
                        
                        return img_base64, None
                    except Exception as img_error:
                        if debug_mode:
                            debug_info.append(f"  ❌ 이미지 변환 실패: {str(img_error)}")
                        continue
                else:
                    # JSON 응답 확인
                    try:
                        error_data = response.json()
                        if debug_mode:
                            debug_info.append(f"  ❌ JSON 응답: {error_data}")
                        continue
                    except:
                        if debug_mode:
                            debug_info.append(f"  ❌ 예상치 못한 응답")
                        continue
            
            elif response.status_code == 503:
                try:
                    error_data = response.json()
                    estimated_time = error_data.get('estimated_time', 20)
                    if debug_mode:
                        debug_info.append(f"  ⏳ 모델 로딩 중 (약 {estimated_time}초)")
                    
                    if model_idx == len(HUGGINGFACE_MODELS) - 1:
                        return None, f"⏳ 모델 로딩 중입니다. 약 {estimated_time}초 후 다시 시도해주세요."
                    else:
                        continue
                except:
                    continue
            
            elif response.status_code == 404:
                if debug_mode:
                    debug_info.append(f"  ❌ 404: 모델을 찾을 수 없음")
                continue
            
            elif response.status_code == 401:
                return None, "❌ API 키가 유효하지 않습니다. Secrets에서 HUGGINGFACE_API_KEY를 확인해주세요."
            
            elif response.status_code == 429:
                return None, "⚠️ API 사용 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
            
            else:
                if debug_mode:
                    try:
                        error_data = response.json()
                        debug_info.append(f"  ❌ 에러: {error_data.get('error', 'Unknown')}")
                    except:
                        debug_info.append(f"  ❌ HTTP {response.status_code}")
                continue
                
        except requests.exceptions.Timeout:
            if debug_mode:
                debug_info.append(f"  ⏱️ 타임아웃")
            continue
        
        except requests.exceptions.ConnectionError:
            return None, "❌ 네트워크 연결 오류. 인터넷 연결을 확인해주세요."
        
        except Exception as e:
            if debug_mode:
                debug_info.append(f"  ❌ 예외: {str(e)}")
            if model_idx == len(HUGGINGFACE_MODELS) - 1:
                if debug_mode:
                    return None, "\n".join(debug_info)
                return None, f"❌ 예상치 못한 오류: {str(e)}"
            continue
    
    # 모든 모델 실패
    if debug_mode:
        return None, "\n".join(debug_info)
    
    return None, "❌ 모든 Hugging Face 모델에서 실패했습니다."

def create_emotion_prompt_for_huggingface(emotion_summary, keywords):
    """
    감정과 키워드를 기반으로 Hugging Face용 프롬프트 생성
    """
    # 감정별 스타일 매핑
    emotion_styles = {
        'joy': 'bright, cheerful, warm colors, joyful, sunny, vibrant, happy atmosphere',
        'sadness': 'melancholic, blue tones, gentle rain, soft mood, emotional, peaceful',
        'anger': 'intense, red and orange colors, stormy, powerful, dramatic',
        'anxiety': 'turbulent, purple and grey tones, swirling patterns, uncertain',
        'calmness': 'calm, serene, pastel colors, tranquil, peaceful, gentle'
    }
    
    # 가장 높은 감정 찾기
    dominant_emotion = max(emotion_summary, key=emotion_summary.get)
    style = emotion_styles.get(dominant_emotion, 'balanced, neutral, artistic')
    
    # 키워드를 영어로 간단히 변환 (주요 키워드만)
    keyword_map = {
        '햇빛': 'sunshine', '비': 'rain', '바다': 'ocean', '산': 'mountain',
        '도시': 'city', '숲': 'forest', '밤': 'night', '낮': 'day',
        '친구': 'friends', '가족': 'family', '집': 'home', '공원': 'park',
        '하늘': 'sky', '구름': 'clouds', '꽃': 'flowers', '나무': 'trees',
        '사랑': 'love', '행복': 'happiness', '희망': 'hope'
    }
    
    english_keywords = []
    for k in keywords[:3]:  # 상위 3개만
        if k in keyword_map:
            english_keywords.append(keyword_map[k])
    
    keywords_str = ', '.join(english_keywords) if english_keywords else 'abstract scene'
    
    # 프롬프트 생성
    prompt = f"A beautiful artistic illustration, {style}, featuring {keywords_str}, digital art, high quality, detailed, expressive, emotional artwork, masterpiece"
    
    # Negative prompt
    negative_prompt = "text, words, letters, watermark, signature, blurry, low quality, ugly, distorted, deformed, nsfw, realistic photo"
    
    return prompt, negative_prompt

# Google Drive 이미지 저장 함수 (선택적)
def save_image_to_drive(date_str, image_base64, prompt):
    """
    Google Drive에 이미지 저장 (더 큰 파일 지원)
    Sheets에는 Drive URL만 저장
    """
    try:
        # Google Drive API 사용 (추가 설정 필요)
        # 현재는 압축된 버전만 Sheets에 저장
        return save_metaphor_image(date_str, image_base64, prompt)
    except:
        return save_metaphor_image(date_str, image_base64, prompt)

def save_metaphor_image(date_str, image_base64, prompt):
    """메타포 이미지를 Google Sheets에 저장 (자동 압축)"""
    try:
        original_size = len(image_base64)
        
        # Base64 이미지가 너무 크면 압축
        if original_size > 40000:  # 안전 마진 10000자
            try:
                # Base64를 이미지로 디코딩
                img_data = base64.b64decode(image_base64)
                img = Image.open(BytesIO(img_data))
                
                original_dims = img.size
                
                # 이미지 크기에 따라 압축 레벨 결정
                if original_size > 100000:
                    max_size = (200, 200)
                    quality = 60
                elif original_size > 70000:
                    max_size = (256, 256)
                    quality = 65
                else:
                    max_size = (300, 300)
                    quality = 70
                
                # 이미지 리사이즈
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # JPEG로 변환하여 용량 줄이기
                buffered = BytesIO()
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(buffered, format="JPEG", quality=quality, optimize=True)
                
                # 다시 Base64로 인코딩
                compressed_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                # 여전히 크면 더 압축
                attempt = 1
                while len(compressed_base64) > 40000 and attempt < 5:
                    quality = max(30, quality - 10)
                    max_size = (max(100, max_size[0] - 50), max(100, max_size[1] - 50))
                    
                    img_data = base64.b64decode(image_base64)
                    img = Image.open(BytesIO(img_data))
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    buffered = BytesIO()
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    img.save(buffered, format="JPEG", quality=quality, optimize=True)
                    compressed_base64 = base64.b64encode(buffered.getvalue()).decode()
                    attempt += 1
                
                compressed_size = len(compressed_base64)
                compression_ratio = (1 - compressed_size / original_size) * 100
                
                if compressed_size < 40000:
                    image_base64 = compressed_base64
                    st.success(f"📦 이미지 압축 완료: {original_dims} → {img.size}, {compression_ratio:.1f}% 절감")
                else:
                    st.warning("⚠️ 이미지가 너무 큽니다. 썸네일만 저장됩니다.")
                    image_base64 = "too_large_thumbnail_only"
                
            except Exception as compress_error:
                st.warning(f"⚠️ 이미지 압축 실패: {compress_error}")
                image_base64 = "compression_failed"
        
        all_values = metaphor_worksheet.get_all_values()
        row_index = None
        
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) > 0 and row[0] == date_str:
                row_index = idx
                break
        
        # 프롬프트도 길이 제한
        if len(prompt) > 1000:
            prompt = prompt[:997] + "..."
        
        row_data = [date_str, image_base64, prompt, datetime.now().isoformat()]
        
        if row_index:
            metaphor_worksheet.update(f'A{row_index}:D{row_index}', [row_data])
        else:
            metaphor_worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        # 더 상세한 에러 메시지
        error_msg = str(e)
        if "50000 characters" in error_msg:
            st.error("❌ 이미지가 너무 큽니다. 압축을 시도했으나 실패했습니다.")
            st.info("💡 이미지는 브라우저에서 다운로드할 수 있으며, 다음번에는 자동으로 더 작은 크기로 생성됩니다.")
        else:
            st.error(f"❌ 저장 오류: {e}")
        return False

def load_metaphor_image(date_str):
    """저장된 메타포 이미지 불러오기"""
    try:
        records = metaphor_worksheet.get_all_records()
        for record in records:
            if record.get('date') == date_str:
                image_url = record.get('image_url')
                prompt = record.get('prompt')
                
                # 특수 표시 확인
                if image_url in ["too_large", "too_large_thumbnail_only", "compression_failed"]:
                    st.info("💡 이 날짜의 원본 이미지는 너무 커서 저장되지 않았습니다.")
                    return None, prompt
                
                return image_url, prompt
        return None, None
    except:
        return None, None

# 데이터 함수들
def load_data_from_sheets():
    try:
        records = diary_worksheet.get_all_records()
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
                    'date': date_str, 'content': record.get('content', ''),
                    'keywords': keywords, 'total_score': float(record.get('total_score', 0)),
                    'joy': int(record.get('joy', 0)), 'sadness': int(record.get('sadness', 0)),
                    'anger': int(record.get('anger', 0)), 'anxiety': int(record.get('anxiety', 0)),
                    'calmness': int(record.get('calmness', 0)), 'message': record.get('message', '')
                }
        return data
    except:
        return {}

def save_data_to_sheets(date_str, item_data):
    try:
        all_values = diary_worksheet.get_all_values()
        row_index = None
        
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) > 0 and row[0] == date_str:
                row_index = idx
                break
        
        keywords_str = json.dumps(item_data['keywords'], ensure_ascii=False)
        row_data = [
            str(date_str), str(item_data['content']), str(keywords_str), float(item_data['total_score']),
            int(item_data['joy']), int(item_data['sadness']), int(item_data['anger']),
            int(item_data['anxiety']), int(item_data['calmness']), str(item_data['message']),
            datetime.now().isoformat()
        ]
        
        if row_index:
            diary_worksheet.update(f'A{row_index}:K{row_index}', [row_data])
        else:
            diary_worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        st.error(f"저장 오류: {e}")
        return False

def delete_data_from_sheets(date_str):
    try:
        all_values = diary_worksheet.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if row[0] == date_str:
                diary_worksheet.delete_rows(idx)
                return True
        return False
    except:
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
    except:
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
    except:
        return {}

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

def compare_periods(items):
    if len(items) < 14:
        return None
    
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

def create_emotion_flow_chart(items):
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        recent_items = items[-14:] if len(items) >= 14 else items
        dates = [item['date'][-5:] for item in recent_items]
        
        emotions = {
            'Joy': [item['joy'] for item in recent_items],
            'Sadness': [item['sadness'] for item in recent_items],
            'Anger': [item['anger'] for item in recent_items],
            'Anxiety': [item['anxiety'] for item in recent_items],
            'Calm': [item['calmness'] for item in recent_items]
        }
        
        colors = {'Joy': '#FFD700', 'Sadness': '#4169E1', 'Anger': '#DC143C', 'Anxiety': '#FF8C00', 'Calm': '#32CD32'}
        
        for name, values in emotions.items():
            ax.plot(dates, values, marker='o', label=name, color=colors[name], linewidth=2)
        
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Score', fontsize=10)
        ax.set_title('Emotion Flow', fontsize=12, fontweight='bold')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, fontsize=8)
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf
    except:
        return None

def create_emotion_network(items):
    try:
        fig, ax = plt.subplots(figsize=(8, 6))
        recent_items = items[-30:] if len(items) >= 30 else items
        
        emotions = {
            'Joy': [item['joy'] for item in recent_items],
            'Sad': [item['sadness'] for item in recent_items],
            'Anger': [item['anger'] for item in recent_items],
            'Anxiety': [item['anxiety'] for item in recent_items],
            'Calm': [item['calmness'] for item in recent_items]
        }
        
        G = nx.Graph()
        for emotion in emotions.keys():
            G.add_node(emotion)
        
        for i, e1 in enumerate(list(emotions.keys())):
            for j, e2 in enumerate(list(emotions.keys())):
                if i < j:
                    corr = np.corrcoef(emotions[e1], emotions[e2])[0, 1]
                    if abs(corr) > 0.3:
                        G.add_edge(e1, e2, weight=abs(corr))
        
        pos = nx.spring_layout(G, k=1.5, iterations=50)
        colors = ['#FFD700', '#4169E1', '#DC143C', '#FF8C00', '#32CD32']
        nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=2000, alpha=0.9, ax=ax)
        
        edges = G.edges()
        weights = [G[u][v]['weight'] for u, v in edges]
        nx.draw_networkx_edges(G, pos, width=[w*4 for w in weights], alpha=0.5, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold', ax=ax)
        
        ax.set_title('Emotion Network', fontsize=12, fontweight='bold', pad=15)
        ax.axis('off')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf
    except:
        return None

def create_goal_flowchart(items):
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        recent_items = items[-14:] if len(items) >= 14 else items
        dates = [item['date'][-5:] for item in recent_items]
        scores = [item['total_score'] for item in recent_items]
        
        ax.plot(dates, scores, marker='o', color='#1E90FF', linewidth=3, markersize=8, label='Motivation')
        
        avg_score = sum(scores) / len(scores)
        ax.axhline(y=avg_score, color='r', linestyle='--', linewidth=2, alpha=0.7, label=f'Avg: {avg_score:.1f}')
        ax.axhline(y=8, color='g', linestyle='--', linewidth=2, alpha=0.5, label='Target: 8.0')
        
        ax.fill_between(range(len(dates)), scores, avg_score, 
                        where=[s >= avg_score for s in scores],
                        alpha=0.3, color='green', label='Rising')
        ax.fill_between(range(len(dates)), scores, avg_score,
                        where=[s < avg_score for s in scores],
                        alpha=0.3, color='red', label='Falling')
        
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Level', fontsize=10)
        ax.set_title('Goal Flow', fontsize=12, fontweight='bold')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, 10])
        plt.xticks(range(len(dates)), dates, rotation=45, fontsize=8)
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf
    except:
        return None

def create_metaphor_prompt(items):
    recent_items = items[-7:] if len(items) >= 7 else items
    emotions_summary = {'joy': 0, 'sadness': 0, 'anger': 0, 'anxiety': 0, 'calmness': 0}
    
    for item in recent_items:
        for emotion in emotions_summary:
            emotions_summary[emotion] += item[emotion]
    
    dominant_emotion = max(emotions_summary, key=emotions_summary.get)
    
    metaphors = {
        'joy': 'Bright sunshine, blooming flowers, soaring birds',
        'sadness': 'Rainy sky, calm lake, falling leaves',
        'anger': 'Burning flames, storm, rough waves',
        'anxiety': 'Dark maze, tangled threads, flickering flame',
        'calmness': 'Calm sea, peaceful forest, sky above clouds'
    }
    
    return f"{metaphors[dominant_emotion]}", dominant_emotion, emotions_summary

def gemini_chat(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return None

def sentiment_analysis(content):
    prompt = f"""
    일기 감정 분석. JSON으로 답변:
    {content}
    형식: {{"keywords": ["k1", "k2", "k3", "k4", "k5"], "joy": 0-10, "sadness": 0-10, "anger": 0-10, "anxiety": 0-10, "calmness": 0-10}}
    """
    try:
        response_text = gemini_chat(prompt)
        if response_text:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response_text[start:end])
    except:
        pass
    return {"keywords": ["일기", "오늘", "하루", "생각", "마음"], "joy": 5, "sadness": 3, "anger": 2, "anxiety": 3, "calmness": 4}

def generate_message(today_data, recent_data):
    prompt = f"일기 앱 AI. 따뜻한 메시지 JSON: 오늘:{today_data} 최근:{recent_data} 형식: {{\"message\": \"응원 😊\"}}"
    try:
        response_text = gemini_chat(prompt)
        if response_text:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response_text[start:end])["message"]
    except:
        pass
    return "오늘도 일기를 써주셔서 감사해요! 😊"

def get_expert_advice(expert_type, diary_data):
    sorted_diaries = sorted(diary_data.values(), key=lambda x: x['date'])
    recent_diaries = sorted_diaries[-30:]
    diary_summary = [f"날짜: {d['date']}, 내용: {d['content'][:100]}..., 점수: {d['total_score']}" for d in recent_diaries]
    diary_text = "\n".join(diary_summary)
    
    prompt = f"당신은 {expert_type}입니다.\n{diary_text}\n\n분석하여 JSON으로: {{\"advice\": \"조언\", \"has_content\": true/false}}"
    
    try:
        with st.spinner(f'🤖 {expert_type} 분석 중...'):
            response_text = gemini_chat(prompt)
            if response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    return json.loads(response_text[start:end])
    except:
        pass
    return {"advice": "조언을 생성할 수 없습니다.", "has_content": False}

def calc_total_score(item):
    score = (2 * item["joy"] + 1.5 * item["calmness"] - 2 * item["sadness"] - 1.5 * item["anxiety"] - 1.5 * item["anger"] + 50)
    return round(score / 8.5, 2)

# 메인 화면
st.title("📱 감정 일기")

# 🔍 클로바 API 상태 진단
with st.expander("🔧 클로바 API 진단", expanded=True):
    st.markdown("### 🔍 현재 상태")
    
    # 1. 환경 확인
    st.write(f"**실행 환경:** {'Streamlit Cloud' if 'secrets' in dir(st) else '로컬'}")
    
    # 2. API 키 존재 여부
    col1, col2 = st.columns(2)
    with col1:
        if NAVER_CLIENT_ID:
            st.success(f"✅ CLIENT_ID: {len(NAVER_CLIENT_ID)}자")
        else:
            st.error("❌ CLIENT_ID 없음")
    
    with col2:
        if NAVER_CLIENT_SECRET:
            st.success(f"✅ CLIENT_SECRET: {len(NAVER_CLIENT_SECRET)}자")
        else:
            st.error("❌ CLIENT_SECRET 없음")
    
    # 3. 클로바 활성화 상태
    st.divider()
    if CLOVA_ENABLED:
        st.success("✅ **클로바 API 활성화됨!** 음성 입력 사용 가능")
    else:
        st.error("❌ **클로바 API 비활성화됨!** 음성 입력 사용 불가")
        
        st.markdown("### 🛠️ 해결 방법")
        
        # Streamlit Cloud인 경우
        if 'secrets' in dir(st):
            st.info("""
            **Streamlit Cloud 설정:**
            1. 우측 상단 [⚙️ Settings] 클릭
            2. [Secrets] 탭 선택
            3. 다음 내용 추가:
            """)
            st.code("""NAVER_CLIENT_ID = "your_client_id_here"
NAVER_CLIENT_SECRET = "your_client_secret_here"
GEMINI_API_KEY = "your_gemini_key_here"
SPREADSHEET_ID = "your_spreadsheet_id"

[gcp_service_account]
# ... (기존 Google Cloud 설정)
""", language="toml")
        else:
            # 로컬 환경
            st.info("""
            **로컬 환경 설정:**
            프로젝트 폴더에 `.env` 파일 생성 후:
            """)
            st.code("""NAVER_CLIENT_ID=your_client_id_here
NAVER_CLIENT_SECRET=your_client_secret_here
GEMINI_API_KEY=your_gemini_key_here""", language="bash")
        
        st.markdown("### 📋 네이버 클라우드 API 키 발급")
        st.markdown("""
        1. [네이버 클라우드 플랫폼](https://console.ncloud.com/) 접속
        2. 로그인 후 **[Services]** → **[AI·NAVER API]**
        3. **[CLOVA Speech Recognition (CSR)]** 선택
        4. **[이용 신청하기]** 클릭
        5. **[마이페이지]** → **[인증키 관리]**에서 키 확인
        """)
        
        st.warning("⚠️ 키 설정 후 반드시 앱을 재시작하세요! (Settings → Reboot app)")
    
    # 4. 테스트 버튼
    if CLOVA_ENABLED:
        st.divider()
        st.markdown("### 🧪 API 연결 테스트")
        st.info("아래 '✍️ 쓰기' 탭에서 음성을 녹음하고 '📝 변환' 버튼을 눌러 실제 작동을 확인하세요.")

api_status = []
if CLOVA_ENABLED:
    api_status.append("🎤 클로버 95%")
if HUGGINGFACE_ENABLED:
    api_status.append("🎨 Hugging Face")
status_text = " | ".join(["AI 분석", "☁️ 클라우드"] + api_status)
st.caption(status_text)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["✍️ 쓰기", "📊 통계", "📈 그래프", "👨‍⚕️ 전문가", "📊 비교"])

# app_sheets.py의 130번째 줄 근처 (with tab1: 섹션) 전체를 이 코드로 교체하세요
# app_sheets.py의 with tab1: 섹션 전체를 이 코드로 교체하세요

with tab1:
    st.subheader("오늘의 마음")
    data, items = get_latest_data()
    
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    
    selected_date = st.date_input("📅 날짜", value=st.session_state.selected_date)
    st.session_state.selected_date = selected_date
    date_str = selected_date.strftime("%Y-%m-%d")
    
    diary_exists = date_str in data
    
    if data:
        st.success(f"☁️ {len(data)}개 저장")
    
    st.divider()
    
    # ✅ 날짜별 일기 내용을 세션에 저장 (핵심!)
    diary_session_key = f'diary_content_{date_str}'
    
    # 처음 해당 날짜를 선택했을 때 기존 일기 내용을 세션에 로드
    if diary_session_key not in st.session_state:
        if diary_exists:
            st.session_state[diary_session_key] = data[date_str]["content"]
        else:
            st.session_state[diary_session_key] = ""
    
    # 음성 입력
    if CLOVA_ENABLED:
        st.markdown("### 🎤 네이버 클로버 (인식률 95%)")
        col_v1, col_v2 = st.columns([3, 1])
        
        with col_v1:
            audio_file = st.audio_input("🎙️ 녹음")
        with col_v2:
            if audio_file is not None:
                if st.button("📝 변환", use_container_width=True, type="primary", key=f"convert_{date_str}"):
                    with st.spinner("🤖 변환 중..."):
                        text = clova_speech_to_text(audio_file)
                        if not text.startswith("❌"):
                            st.success("✅ 완료!")
                            # ✅ 변환된 텍스트를 세션에 저장
                            st.session_state.voice_text = text
                            st.rerun()
                        else:
                            st.error(text)
        
        # 변환된 텍스트 표시 및 추가/삭제 버튼
        if 'voice_text' in st.session_state and st.session_state.voice_text:
            st.success(f"🎤 {st.session_state.voice_text}")
            col_a, col_c = st.columns(2)
            
            with col_a:
                if st.button("📋 추가", use_container_width=True, key=f"append_{date_str}"):
                    # ✅ 핵심: 기존 내용에 음성 텍스트를 직접 추가
                    current_content = st.session_state[diary_session_key]
                    
                    # 기존 내용이 있으면 두 줄 띄우고 추가
                    if current_content.strip():
                        st.session_state[diary_session_key] = current_content + "\n\n" + st.session_state.voice_text
                    else:
                        st.session_state[diary_session_key] = st.session_state.voice_text
                    
                    st.success("✅ 텍스트가 추가되었습니다!")
                    # 음성 텍스트는 유지 (다시 추가 가능)
                    st.rerun()
            
            with col_c:
                if st.button("🗑️ 지우기", use_container_width=True, key=f"clear_{date_str}"):
                    # 음성 텍스트만 삭제
                    del st.session_state.voice_text
                    st.rerun()
    
    st.divider()
    
    # ✅ 텍스트 입력란 - 세션 상태를 직접 참조
    content = st.text_area(
        "📝 오늘 하루는?", 
        value=st.session_state[diary_session_key],  # 세션에서 직접 가져오기
        height=200, 
        placeholder="입력 또는 음성...",
        key=f"textarea_{date_str}"
    )
    
    # ✅ 사용자가 텍스트를 직접 수정하면 세션에 반영
    if content != st.session_state[diary_session_key]:
        st.session_state[diary_session_key] = content
    
    # 저장 및 삭제 버튼
    col1, col2 = st.columns([3, 1])
    with col1:
        save_clicked = st.button("💾 저장", type="primary", use_container_width=True, key=f"save_{date_str}")
    with col2:
        if diary_exists:
            if st.button("🗑️", help="삭제", key=f"delete_{date_str}"):
                st.session_state.confirm_delete = date_str
                st.rerun()
        else:
            if st.button("🗑️", help="전체 지우기", key=f"clear_all_{date_str}"):
                # 입력란 완전 초기화
                st.session_state[diary_session_key] = ""
                if 'voice_text' in st.session_state:
                    del st.session_state.voice_text
                st.rerun()
    
    # 삭제 확인
    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        st.warning(f"⚠️ {st.session_state.confirm_delete} 삭제?")
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button("✅ 예", type="primary", key="confirm_yes"):
                if delete_data_from_sheets(st.session_state.confirm_delete):
                    st.success("🗑️ 삭제됨")
                    # 세션에서도 제거
                    del_key = f'diary_content_{st.session_state.confirm_delete}'
                    if del_key in st.session_state:
                        del st.session_state[del_key]
                del st.session_state.confirm_delete
                st.rerun()
        with col_n:
            if st.button("❌ 아니오", key="confirm_no"):
                del st.session_state.confirm_delete
                st.rerun()
        save_clicked = False
    
    # 💾 저장 처리
    if save_clicked:
        # ✅ 세션에서 최신 내용 가져오기
        final_content = st.session_state[diary_session_key]
        
        if final_content.strip():
            with st.spinner('🤖 분석 중...'):
                try:
                    analyzed = sentiment_analysis(final_content)
                    data, items = get_latest_data()
                    
                    today_data = {
                        "date": date_str, 
                        "keywords": analyzed["keywords"], 
                        "joy": analyzed["joy"], 
                        "sadness": analyzed["sadness"], 
                        "anger": analyzed["anger"], 
                        "anxiety": analyzed["anxiety"], 
                        "calmness": analyzed["calmness"]
                    }
                    
                    recent_data = [{
                        "date": i["date"], 
                        "keywords": i["keywords"], 
                        "joy": i["joy"], 
                        "sadness": i["sadness"], 
                        "anger": i["anger"], 
                        "anxiety": i["anxiety"], 
                        "calmness": i["calmness"]
                    } for i in items[-7:]]
                    
                    message = generate_message(today_data, recent_data)
                    
                    new_item = {
                        "date": date_str, 
                        "content": final_content,  # 세션에서 가져온 최종 내용
                        "keywords": analyzed["keywords"],
                        "total_score": calc_total_score(analyzed),
                        "joy": analyzed["joy"], 
                        "sadness": analyzed["sadness"],
                        "anger": analyzed["anger"], 
                        "anxiety": analyzed["anxiety"],
                        "calmness": analyzed["calmness"], 
                        "message": message
                    }
                    
                    if save_data_to_sheets(date_str, new_item):
                        st.success("✅ 저장!")
                        st.balloons()
                        
                        # ✅ 저장 성공 후 음성 텍스트만 정리 (일기 내용은 유지)
                        if 'voice_text' in st.session_state:
                            del st.session_state.voice_text
                        
                        # 저장된 내용으로 세션 업데이트
                        st.session_state[diary_session_key] = final_content
                        
                        st.rerun()
                    else:
                        st.error("❌ 저장 실패! Google Sheets 연결을 확인하세요.")
                        
                except Exception as e:
                    st.error(f"❌ 오류 발생: {str(e)}")
        else:
            st.warning("⚠️ 내용을 입력해주세요!")
    
    # 일기 정보 표시
    if 'confirm_delete' not in st.session_state:
        st.divider()
        if diary_exists:
            item = data[date_str]
            ts = item["total_score"]
            emoji, color = ("😄", "green") if ts >= 8 else ("😊", "blue") if ts >= 6 else ("😐", "orange") if ts >= 4 else ("😢", "red")
            
            st.markdown(f"### 🎯 점수: **:{color}[{ts}/10]** {emoji}")
            st.write("**🎭 세부:**")
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
            if item["message"]:
                st.success(f"💌 {item['message']}")
        else:
            st.info("💡 일기를 쓰면 AI가 분석!")# app_sheets.py의 with tab1: 섹션 전체를 이 코드로 교체하세요

with tab1:
    st.subheader("오늘의 마음")
    data, items = get_latest_data()
    
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    
    selected_date = st.date_input("📅 날짜", value=st.session_state.selected_date)
    st.session_state.selected_date = selected_date
    date_str = selected_date.strftime("%Y-%m-%d")
    
    diary_exists = date_str in data
    
    if data:
        st.success(f"☁️ {len(data)}개 저장")
    
    st.divider()
    
    # ✅ 날짜별 일기 내용을 세션에 저장 (핵심!)
    diary_session_key = f'diary_content_{date_str}'
    
    # 처음 해당 날짜를 선택했을 때 기존 일기 내용을 세션에 로드
    if diary_session_key not in st.session_state:
        if diary_exists:
            st.session_state[diary_session_key] = data[date_str]["content"]
        else:
            st.session_state[diary_session_key] = ""
    
    # 음성 입력
    if CLOVA_ENABLED:
        st.markdown("### 🎤 네이버 클로버 (인식률 95%)")
        col_v1, col_v2 = st.columns([3, 1])
        
        with col_v1:
            audio_file = st.audio_input("🎙️ 녹음")
        with col_v2:
            if audio_file is not None:
                if st.button("📝 변환", use_container_width=True, type="primary", key=f"convert_{date_str}"):
                    with st.spinner("🤖 변환 중..."):
                        text = clova_speech_to_text(audio_file)
                        if not text.startswith("❌"):
                            st.success("✅ 완료!")
                            # ✅ 변환된 텍스트를 세션에 저장
                            st.session_state.voice_text = text
                            st.rerun()
                        else:
                            st.error(text)
        
        # 변환된 텍스트 표시 및 추가/삭제 버튼
        if 'voice_text' in st.session_state and st.session_state.voice_text:
            st.success(f"🎤 {st.session_state.voice_text}")
            col_a, col_c = st.columns(2)
            
            with col_a:
                if st.button("📋 추가", use_container_width=True, key=f"append_{date_str}"):
                    # ✅ 핵심: 기존 내용에 음성 텍스트를 직접 추가
                    current_content = st.session_state[diary_session_key]
                    
                    # 기존 내용이 있으면 두 줄 띄우고 추가
                    if current_content.strip():
                        st.session_state[diary_session_key] = current_content + "\n\n" + st.session_state.voice_text
                    else:
                        st.session_state[diary_session_key] = st.session_state.voice_text
                    
                    st.success("✅ 텍스트가 추가되었습니다!")
                    # 음성 텍스트는 유지 (다시 추가 가능)
                    st.rerun()
            
            with col_c:
                if st.button("🗑️ 지우기", use_container_width=True, key=f"clear_{date_str}"):
                    # 음성 텍스트만 삭제
                    del st.session_state.voice_text
                    st.rerun()
    
    st.divider()
    
    # ✅ 텍스트 입력란 - 세션 상태를 직접 참조
    content = st.text_area(
        "📝 오늘 하루는?", 
        value=st.session_state[diary_session_key],  # 세션에서 직접 가져오기
        height=200, 
        placeholder="입력 또는 음성...",
        key=f"textarea_{date_str}"
    )
    
    # ✅ 사용자가 텍스트를 직접 수정하면 세션에 반영
    if content != st.session_state[diary_session_key]:
        st.session_state[diary_session_key] = content
    
    # 저장 및 삭제 버튼
    col1, col2 = st.columns([3, 1])
    with col1:
        save_clicked = st.button("💾 저장", type="primary", use_container_width=True, key=f"save_{date_str}")
    with col2:
        if diary_exists:
            if st.button("🗑️", help="삭제", key=f"delete_{date_str}"):
                st.session_state.confirm_delete = date_str
                st.rerun()
        else:
            if st.button("🗑️", help="전체 지우기", key=f"clear_all_{date_str}"):
                # 입력란 완전 초기화
                st.session_state[diary_session_key] = ""
                if 'voice_text' in st.session_state:
                    del st.session_state.voice_text
                st.rerun()
    
    # 삭제 확인
    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        st.warning(f"⚠️ {st.session_state.confirm_delete} 삭제?")
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button("✅ 예", type="primary", key="confirm_yes"):
                if delete_data_from_sheets(st.session_state.confirm_delete):
                    st.success("🗑️ 삭제됨")
                    # 세션에서도 제거
                    del_key = f'diary_content_{st.session_state.confirm_delete}'
                    if del_key in st.session_state:
                        del st.session_state[del_key]
                del st.session_state.confirm_delete
                st.rerun()
        with col_n:
            if st.button("❌ 아니오", key="confirm_no"):
                del st.session_state.confirm_delete
                st.rerun()
        save_clicked = False
    
    # 💾 저장 처리
    if save_clicked:
        # ✅ 세션에서 최신 내용 가져오기
        final_content = st.session_state[diary_session_key]
        
        if final_content.strip():
            with st.spinner('🤖 분석 중...'):
                try:
                    analyzed = sentiment_analysis(final_content)
                    data, items = get_latest_data()
                    
                    today_data = {
                        "date": date_str, 
                        "keywords": analyzed["keywords"], 
                        "joy": analyzed["joy"], 
                        "sadness": analyzed["sadness"], 
                        "anger": analyzed["anger"], 
                        "anxiety": analyzed["anxiety"], 
                        "calmness": analyzed["calmness"]
                    }
                    
                    recent_data = [{
                        "date": i["date"], 
                        "keywords": i["keywords"], 
                        "joy": i["joy"], 
                        "sadness": i["sadness"], 
                        "anger": i["anger"], 
                        "anxiety": i["anxiety"], 
                        "calmness": i["calmness"]
                    } for i in items[-7:]]
                    
                    message = generate_message(today_data, recent_data)
                    
                    new_item = {
                        "date": date_str, 
                        "content": final_content,  # 세션에서 가져온 최종 내용
                        "keywords": analyzed["keywords"],
                        "total_score": calc_total_score(analyzed),
                        "joy": analyzed["joy"], 
                        "sadness": analyzed["sadness"],
                        "anger": analyzed["anger"], 
                        "anxiety": analyzed["anxiety"],
                        "calmness": analyzed["calmness"], 
                        "message": message
                    }
                    
                    if save_data_to_sheets(date_str, new_item):
                        st.success("✅ 저장!")
                        st.balloons()
                        
                        # ✅ 저장 성공 후 음성 텍스트만 정리 (일기 내용은 유지)
                        if 'voice_text' in st.session_state:
                            del st.session_state.voice_text
                        
                        # 저장된 내용으로 세션 업데이트
                        st.session_state[diary_session_key] = final_content
                        
                        st.rerun()
                    else:
                        st.error("❌ 저장 실패! Google Sheets 연결을 확인하세요.")
                        
                except Exception as e:
                    st.error(f"❌ 오류 발생: {str(e)}")
        else:
            st.warning("⚠️ 내용을 입력해주세요!")
    
    # 일기 정보 표시
    if 'confirm_delete' not in st.session_state:
        st.divider()
        if diary_exists:
            item = data[date_str]
            ts = item["total_score"]
            emoji, color = ("😄", "green") if ts >= 8 else ("😊", "blue") if ts >= 6 else ("😐", "orange") if ts >= 4 else ("😢", "red")
            
            st.markdown(f"### 🎯 점수: **:{color}[{ts}/10]** {emoji}")
            st.write("**🎭 세부:**")
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
            if item["message"]:
                st.success(f"💌 {item['message']}")
        else:
            st.info("💡 일기를 쓰면 AI가 분석!")
           
with tab2:
    st.subheader("📊 통계")
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 첫 일기를 써보세요!")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📈 평균", f"{calc_average_total_score(items)}점")
            st.metric("✏️ 글자", f"{calc_char_count(items):,}자")
        with col2:
            st.metric("📚 일기", f"{len(items)}개")
            st.metric("📅 월", f"{len(set([i['date'][:7] for i in items]))}개월")
        
        st.divider()
        st.write("🏷️ **키워드 TOP 10**")
        kw = calc_keyword_count(items)
        if kw:
            sorted_kw = sorted(kw.items(), key=lambda x: x[1], reverse=True)[:10]
            for i, (k, c) in enumerate(sorted_kw):
                if i < 3:
                    st.markdown(f"### {['🥇','🥈','🥉'][i]} **{k}** `{c}회`")
                else:
                    st.markdown(f"**{i+1}.** {k} `{c}회`")

with tab3:
    st.subheader("📈 그래프")
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기 2개 이상 필요")
    else:
        st.write("**🎯 감정 점수**")
        scores = [{"날짜": i["date"][5:], "점수": i["total_score"]} for i in items[-14:]]
        st.line_chart(scores, x="날짜", y="점수", height=250)
        
        st.write("**🎭 감정별 변화**")
        emo = [{"날짜": i["date"][5:], "😄기쁨": i["joy"], "😌평온": i["calmness"],
               "😰불안": i["anxiety"], "😢슬픔": i["sadness"], "😡분노": i["anger"]} for i in items[-14:]]
        st.area_chart(emo, x="날짜", y=["😄기쁨", "😌평온", "😰불안", "😢슬픔", "😡분노"], height=250)

with tab4:
    st.subheader("👨‍⚕️ 전문가")
    data, items = get_latest_data()
    
    if not items:
        st.info("📝 일기 필요")
    else:
        st.success(f"📊 {len(items)}개 분석")
        
        dates = sorted([i['date'] for i in items], reverse=True)
        sel_date = st.selectbox("📅 날짜", options=dates, index=0)
        saved = load_expert_advice_from_sheets(sel_date)
        
        if saved:
            st.info(f"💾 저장된 조언: {len(saved)}개")
        
        st.divider()
        
        tabs = st.tabs(["🧠 심리", "💰 재정", "⚖️ 법률", "🏥 의사", "✨ 피부", "💪 운동", "🚀 창업", "🎨 예술", "🧬 임상", "👔 조직"])
        experts = [("심리상담사", "🧠", True), ("재정관리사", "💰", False), ("변호사", "⚖️", False), 
                  ("의사", "🏥", False), ("피부관리사", "✨", False), ("피트니스 트레이너", "💪", False),
                  ("창업 벤처투자자", "🚀", True), ("예술치료사", "🎨", False), ("임상심리사", "🧬", True), 
                  ("조직심리 전문가", "👔", False)]
        
        for idx, (name, icon, chart) in enumerate(experts):
            with tabs[idx]:
                st.markdown(f"### {icon} {name}")
                
                if name in saved:
                    st.success(f"📋 {saved[name]['created_at'][:10]}")
                    st.markdown(saved[name]["advice"])
                    st.divider()
                
                if st.button(f"💬 {name} 조언", key=f"b_{name}", use_container_width=True):
                    if chart and len(items) >= 2:
                        if name in ["심리상담사", "임상심리사"]:
                            flow = create_emotion_flow_chart(items)
                            if flow:
                                st.image(flow, caption="Emotion Flow", use_container_width=True)
                            net = create_emotion_network(items)
                            if net:
                                st.image(net, caption="Network", use_container_width=True)
                        elif name == "창업 벤처투자자":
                            goal = create_goal_flowchart(items)
                            if goal:
                                st.image(goal, caption="Goal", use_container_width=True)
                    
                    if name == "예술치료사":
                        metaphor_text, emotion, emotions_summary = create_metaphor_prompt(items)
                        st.info(f"🎨 **메타포:** {metaphor_text}")
                        
                        # 저장된 이미지 확인
                        saved_img, saved_prompt = load_metaphor_image(sel_date)
                        
                        if saved_img:
                            st.success("💾 저장된 이미지 표시")
                            try:
                                img_data = base64.b64decode(saved_img)
                                st.image(img_data, caption="Metaphor Image", use_container_width=True)
                                
                                # 재생성 버튼
                                if st.button("🔄 새 이미지 생성", key="regenerate_img", use_container_width=True):
                                    st.session_state.force_regenerate = True
                                    st.rerun()
                            except Exception as decode_error:
                                st.warning(f"⚠️ 저장된 이미지 로드 실패: {str(decode_error)}")
                                st.info("새 이미지를 생성합니다...")
                                saved_img = None  # 새로 생성하도록
                        
                        # 새 이미지 생성 (저장된 이미지가 없거나 재생성 요청 시)
                        if not saved_img or st.session_state.get('force_regenerate', False):
                            if st.session_state.get('force_regenerate', False):
                                st.session_state.force_regenerate = False
                            
                            # 이미지 생성 방법 선택
                            generation_method = st.radio(
                                "이미지 생성 방법",
                                ["🌟 Pollinations (무료, 빠름, 추천)", "🤗 Hugging Face (API 키 필요)"],
                                key="gen_method",
                                horizontal=True
                            )
                            
                            # 디버그 모드
                            debug_mode = st.checkbox("🔧 디버그 모드", value=False, help="상세한 에러 정보 표시")
                            
                            if "Pollinations" in generation_method:
                                # Pollinations.ai 사용 (무료, API 키 불필요)
                                with st.spinner("🌟 Pollinations AI로 이미지 생성 중... (무료, 빠름)"):
                                    # 최근 일기에서 키워드 추출
                                    recent_keywords = []
                                    for item in items[-7:]:
                                        recent_keywords.extend(item['keywords'])
                                    
                                    # 프롬프트 생성
                                    prompt, negative_prompt = create_emotion_prompt_for_huggingface(
                                        emotions_summary, 
                                        recent_keywords
                                    )
                                    
                                    # 프롬프트 미리보기
                                    with st.expander("🔍 생성 프롬프트 보기"):
                                        st.code(f"Prompt: {prompt}")
                                        st.info("📌 Pollinations.ai는 완전 무료이며 API 키가 필요없습니다!")
                                    
                                    # Pollinations로 이미지 생성
                                    img_base64, error = generate_image_with_pollinations(prompt)
                                    
                                    if img_base64:
                                        try:
                                            img_data = base64.b64decode(img_base64)
                                            st.success("✅ 이미지 생성 완료!")
                                            st.image(img_data, caption="🌟 Pollinations AI 생성", use_container_width=True)
                                            
                                            # Google Sheets에 저장
                                            with st.spinner("💾 이미지 저장 중..."):
                                                if save_metaphor_image(sel_date, img_base64, prompt):
                                                    st.success("💾 클라우드 저장 완료!")
                                                else:
                                                    st.warning("⚠️ 클라우드 저장 실패 (이미지는 사용 가능)")
                                            
                                            # 다운로드 버튼
                                            st.download_button(
                                                label="📥 이미지 다운로드",
                                                data=img_data,
                                                file_name=f"emotion_art_{sel_date}.png",
                                                mime="image/png",
                                                use_container_width=True,
                                                type="secondary"
                                            )
                                        except Exception as img_error:
                                            st.error(f"❌ 이미지 처리 오류: {str(img_error)}")
                                    else:
                                        st.error(error if error else "이미지 생성 실패")
                            
                            else:
                                # Hugging Face 사용
                                if HUGGINGFACE_ENABLED:
                                    with st.spinner("🤗 Hugging Face AI로 이미지 생성 중... (여러 모델 시도, 최대 60초)"):
                                        # 최근 일기에서 키워드 추출
                                        recent_keywords = []
                                        for item in items[-7:]:
                                            recent_keywords.extend(item['keywords'])
                                        
                                        # 프롬프트 생성
                                        prompt, negative_prompt = create_emotion_prompt_for_huggingface(
                                            emotions_summary, 
                                            recent_keywords
                                        )
                                        
                                        # 프롬프트 미리보기
                                        with st.expander("🔍 생성 프롬프트 보기"):
                                            st.code(f"Prompt: {prompt}\n\nNegative: {negative_prompt}")
                                            st.caption(f"시도할 모델: {', '.join(HUGGINGFACE_MODELS)}")
                                        
                                        # 이미지 생성
                                        img_base64, error = generate_image_with_huggingface(prompt, negative_prompt, debug_mode=debug_mode)
                                        
                                        if img_base64:
                                            try:
                                                img_data = base64.b64decode(img_base64)
                                                st.success("✅ 이미지 생성 완료!")
                                                
                                                if debug_mode and error:
                                                    with st.expander("🔍 디버그 정보"):
                                                        st.code(error)
                                                
                                                st.image(img_data, caption="🤗 Hugging Face AI 생성", use_container_width=True)
                                                
                                                # Google Sheets에 저장
                                                with st.spinner("💾 이미지 저장 중..."):
                                                    if save_metaphor_image(sel_date, img_base64, prompt):
                                                        st.success("💾 클라우드 저장 완료!")
                                                    else:
                                                        st.warning("⚠️ 클라우드 저장 실패 (이미지는 사용 가능)")
                                                
                                                # 다운로드 버튼
                                                st.download_button(
                                                    label="📥 이미지 다운로드",
                                                    data=img_data,
                                                    file_name=f"emotion_art_{sel_date}.png",
                                                    mime="image/png",
                                                    use_container_width=True,
                                                    type="secondary"
                                                )
                                            except Exception as img_error:
                                                st.error(f"❌ 이미지 처리 오류: {str(img_error)}")
                                        else:
                                            if debug_mode:
                                                st.error("❌ 이미지 생성 실패")
                                                with st.expander("🔍 상세 디버그 정보"):
                                                    st.code(error if error else "알 수 없는 오류")
                                            else:
                                                st.error(error if error else "이미지 생성 실패")
                                            
                                            # 대안 제안
                                            st.info("💡 **추천:** 위에서 'Pollinations (무료, 빠름)' 옵션을 선택해보세요!")
                                else:
                                    st.warning("⚠️ Hugging Face API 키가 설정되지 않았습니다.")
                                    st.info("""
                                    **옵션 1: Pollinations 사용 (추천)**
                                    - 위에서 'Pollinations' 옵션 선택
                                    - 완전 무료, API 키 불필요
                                    
                                    **옵션 2: Hugging Face 설정**
                                    1. Hugging Face (https://huggingface.co/) 가입
                                    2. Settings → Access Tokens → New Token
                                    3. Streamlit Cloud → Settings → Secrets
                                    4. `HUGGINGFACE_API_KEY = "hf_your_token"`
                                    """)
                                    st.code('HUGGINGFACE_API_KEY = "hf_..."', language="toml")
                    
                    result = get_expert_advice(name, data)
                    if result.get("has_content"):
                        st.success(f"**{name} 조언:**")
                        st.markdown(result["advice"])
                        save_expert_advice_to_sheets(sel_date, name, result["advice"], result["has_content"])
                        st.success("💾 저장!")
                    else:
                        st.info(result["advice"])
        
        st.divider()
        st.warning("⚠️ AI 조언은 참고용. 전문가 상담 필요 시 반드시 전문의와 상담하세요.")

with tab5:
    st.subheader("📊 기간별 비교")
    data, items = get_latest_data()
    
    if len(items) < 14:
        st.info("📝 14개 일기 필요")
    else:
        comp = compare_periods(items)
        
        if comp:
            st.write("**📈 최근 vs 이전 (1주)**")
            
            emotion_map = {
                'joy': ('😄', '기쁨'),
                'sadness': ('😢', '슬픔'),
                'anger': ('😡', '분노'),
                'anxiety': ('😰', '불안'),
                'calmness': ('😌', '평온')
            }
            
            # 모바일 최적화: 한 줄에 하나씩
            for key, (emoji, name) in emotion_map.items():
                if key in comp:
                    d = comp[key]
                    trend = "📈" if d['trend'] == '상승' else ("📉" if d['trend'] == '하락' else "➡️")
                    
                    # 컴팩트한 표시
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.metric(f"{emoji} {name}", f"{d['recent']:.1f}", f"{d['diff']:+.1f}")
                    with col2:
                        st.caption(f"이전: {d['previous']:.1f}")
                    with col3:
                        st.caption(f"{trend} {d['trend']}")
            
            st.divider()
            
            # 종합 점수
            total = comp['total']
            if total['trend'] == '상승':
                st.success(f"🎉 종합 상승! (+{total['diff']:.1f}점)")
            elif total['trend'] == '하락':
                st.warning(f"😔 종합 하락 ({total['diff']:+.1f}점)")
            else:
                st.info(f"➡️ 종합 유지")

st.divider()
st.markdown("### 💝 매일 감정 기록")
footer_items = ["🤖 AI", "☁️ 클라우드"]
if CLOVA_ENABLED:
    footer_items.append("🎤 클로버 95%")
footer_items.append("🎨 Pollinations (무료)")
if HUGGINGFACE_ENABLED:
    footer_items.append("🤗 HuggingFace")
st.caption(" | ".join(footer_items))



