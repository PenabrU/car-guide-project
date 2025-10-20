import os
import google.generativeai as genai  # 9단계: Gemini AI 라이브러리
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import documentai  # 8단계: Document AI (OCR) 라이브러리

# --- 1. Google Cloud (Document AI - OCR) 설정 ---
# 7단계에서 받은 서비스 계정 키 파일 (backend 폴더에 위치)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account-key.json"

# 8-2단계에서 확인한 본인의 Google Cloud 정보로 수정하세요
PROJECT_ID = "car-guide-project" 
LOCATION = "us" # 8-2단계에서 프로세서를 만든 지역 (예: 'us')
PROCESSOR_ID = "e24b7188dfdbc291" # 8-2단계에서 복사한 프로세서 I

# Document AI 클라이언트 초기화
documentai_client = documentai.DocumentProcessorServiceClient()
processor_name = documentai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

# --- 2. Google AI (Gemini - AI) 설정 ---
# 9-2단계에서 Google AI Studio에서 발급받은 키로 수정하세요
GEMINI_API_KEY = "AIzaSyBY-mIvaT94Qf5mPhgh31CaJmjC4YcTivE" 
genai.configure(api_key=GEMINI_API_KEY)

# (사용자가 작동 확인한 'gemini-2.5-pro' 또는 안정적인 'gemini-1.5-flash' / 'gemini-pro' 사용)
gemini_model = genai.GenerativeModel('gemini-2.5-pro')

# --- 3. Flask 앱(서버) 설정 ---
app = Flask(__name__)
CORS(app)  # 모든 외부 요청 허용 (프론트엔드 연동용)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# uploads 폴더가 없으면 자동으로 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- 4. API 엔드포인트 ---

@app.route("/", methods=['GET'])
def health_check():
    """서버 헬스 체크 API"""
    return jsonify({"status": "ok", "message": "백엔드 서버가 정상 동작 중입니다."})

@app.route("/api/upload", methods=['POST'])
def upload_file_and_analyze():
    """(기능 1) 파일 업로드, OCR 분석, Gemini 리포트 생성을 모두 처리하는 API"""
    
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "파일이 없습니다."}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "파일이 선택되지 않았습니다."}), 400

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        print(f"파일 저장 완료: {file_path}")

        ocr_text_data = "" # OCR 결과를 저장할 변수

        try:
            # --- 8단계: Document AI (OCR) 분석 ---
            print("Document AI 분석 시작...")
            with open(file_path, "rb") as doc_file:
                doc_content = doc_file.read()

            # PDF인지 이미지인지 MIME 타입 확인 (간단하게)
            mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "image/jpeg"

            raw_document = documentai.RawDocument(
                content=doc_content, mime_type=mime_type
            )
            request_doc = documentai.ProcessRequest(
                name=processor_name, raw_document=raw_document
            )
            result = documentai_client.process_document(request=request_doc)
            document = result.document
            
            # Key-Value 데이터를 텍스트(string)로 변환
            for entity in document.entities:
                if entity.confidence > 0.7: # 신뢰도 70% 이상
                    key = entity.type_.replace("_", " ").strip()
                    value = entity.mention_text.strip()
                    if key and value:
                        ocr_text_data += f"{key}: {value}\n"
            
            print("Document AI 분석 완료. 추출된 텍스트:")
            print(ocr_text_data)

            # --- 9단계: Gemini AI (분석) ---
            print("Gemini AI 분석 시작...")
            
            prompt = f"""
            당신은 중고차 성능기록부 분석 전문가입니다.
            다음은 OCR로 추출된 성능기록부의 Key-Value 데이터입니다:
            ---
            {ocr_text_data}
            ---

            이 데이터를 바탕으로, 아래 3가지 항목에 대해 구매자(초보자)가 이해하기 쉽게 분석 리포트를 생성해 주세요.
            각 항목은 Markdown을 사용하여 명확하게 구분하고, 친절한 말투를 사용해 주세요.
            만약 데이터가 부족하거나 항목이 없으면 "정보 없음" 또는 "특이사항 없음"으로 표시해 주세요.

            1.  **종합 브리핑:**
                (예: 이 차는 2018년식 쏘나타로, 주행거리는 양호하나 경미한 사고 이력이 2건 확인됩니다.)

            2.  **사고 및 수리 이력 분석 (가장 중요):**
                (예: 외부 패널(휀더, 도어)에 판금(W) 2곳이 있습니다. 이는 주행 성능에 영향을 주지 않는 경미한 사고로 보입니다. 하지만 주요 골격(프레임) 손상은 없어 안심하셔도 됩니다.)

            3.  **잠재적 리스크 및 조언 (예상 비용 포함):**
                (예: 엔진오일팬에 '미세누유'가 체크되어 있습니다. 당장 수리는 필요 없으나, 1~2년 내 약 15~25만 원의 수리 비용이 발생할 수 있습니다. 구매 시 이 부분을 감안하여 가격 협상을 시도해 보세요.)
            """

            response = gemini_model.generate_content(prompt)
            analysis_result = response.text 
            
            print("Gemini AI 분석 완료.")

            return jsonify({
                "status": "success", 
                "message": f"'{filename}' 파일 분석 성공!",
                "data": analysis_result
            })

        except Exception as e:
            print(f"AI 분석 중 오류 발생: {e}")
            return jsonify({"status": "error", "message": f"AI 분석 중 오류가 발생했습니다: {e}"}), 500
        
        finally:
            # 성공하든 실패하든 임시 파일 삭제
            if os.path.exists(file_path):
                 os.remove(file_path)
                 print(f"임시 파일 삭제 완료: {file_path}")

@app.route("/api/recommend", methods=['POST'])
def recommend_car():
    """(기능 2) 10단계: AI 차량 추천 API"""
    
    data = request.json
    if not data or 'lifestyle_text' not in data:
        return jsonify({"status": "error", "message": "요청 내용이 없습니다."}), 400

    user_text = data['lifestyle_text']
    print(f"사용자 요청 텍스트: {user_text}")

    try:
        prompt = f"""
        당신은 중고차 추천 전문 컨설턴트입니다.
        한 사용자가 다음과 같이 자신에게 맞는 차를 찾아달라고 요청했습니다:
        ---
        "{user_text}"
        ---

        이 사용자의 예산, 나이, 가족 구성, 주 용도 등을 파악하여, 이 사람에게 가장 잘 어울리는 중고차 모델 3가지를 추천해 주세요.
        아래 형식을 정확히 지켜서, 추천 이유와 예상 중고차 시세(예: 1500~2000만 원)를 포함하여 생성해 주세요.

        1.  **추천 모델 1 (예: 싼타페 TM)**
            * **추천 이유:** (예: 30대 가족의 패밀리카로 가장 무난하며, 캠핑용 짐을 싣기에 충분한 트렁크 공간을 제공합니다.)
            * **예상 시세:** (예: 2000~2500만 원)

        2.  **추천 모델 2 (예: 기아 쏘렌토 4세대)**
            * **추천 이유:** (예: ...)
            * **예상 시세:** (예: ...)

        3.  **추천 모델 3 (예: 르노 QM6)**
            * **추천 이유:** (예: ...)
            * **예상 시세:** (예: ...)
        """
        
        print("Gemini AI 추천 시작...")
        response = gemini_model.generate_content(prompt)
        recommendation_result = response.text
        print("Gemini AI 추천 완료.")

        return jsonify({
            "status": "success",
            "message": "차량 추천 성공!",
            "data": recommendation_result
        })

    except Exception as e:
        print(f"AI 추천 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": "AI 추천 중 오류가 발생했습니다."}), 500

# --- 5. Flask 서버 실행 ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)