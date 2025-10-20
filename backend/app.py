import os
import google.generativeai as genai
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import documentai
from dotenv import load_dotenv # 1. dotenv 라이브러리 임포트

load_dotenv() # 2. .env 파일에서 환경 변수를 불러옴

# --- 1. Google Cloud (Document AI - OCR) 설정 ---
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account-key.json"

# 3. .env 파일에서 값 불러오기
PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
LOCATION = os.getenv("GOOGLE_LOCATION")
PROCESSOR_ID = os.getenv("GOOGLE_PROCESSOR_ID")

documentai_client = documentai.DocumentProcessorServiceClient()
processor_name = documentai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

# --- 2. Google AI (Gemini - AI) 설정 ---
# 3. .env 파일에서 값 불러오기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

gemini_model = genai.GenerativeModel('gemini-2.5-pro')

# --- 3. Flask 앱(서버) 설정 ---
app = Flask(__name__)
# ... (이하 모든 코드는 이전과 동일합니다) ...
# (이 아래 부분은 수정할 필요 없습니다)
CORS(app)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- 4. API 엔드포인트 ---
@app.route("/", methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "백엔드 서버가 정상 동작 중입니다."})

@app.route("/api/upload", methods=['POST'])
def upload_file_and_analyze():
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

        ocr_full_text = ""

        try:
            print("Document AI 분석 시작...")
            with open(file_path, "rb") as doc_file:
                doc_content = doc_file.read()

            mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "image/jpeg"

            raw_document = documentai.RawDocument(
                content=doc_content, mime_type=mime_type
            )
            request_doc = documentai.ProcessRequest(
                name=processor_name, raw_document=raw_document
            )
            result = documentai_client.process_document(request=request_doc)
            document = result.document
            
            ocr_full_text = document.text
            
            print("Document AI 분석 완료. 추출된 텍스트(뭉텅이):")
            print(ocr_full_text[:500])

            print("Gemini AI 분석 시작...")
            
            prompt = f"""
            당신은 중고차 성능기록부 분석 전문가입니다.
            다음은 PDF에서 추출된 성능기록부의 '전체 텍스트'입니다. 이 텍스트는 순서가 섞여있을 수 있습니다:
            ---
            {ocr_full_text}
            ---

            이 텍스트를 '당신이 직접 해석'하여, 아래 3가지 항목에 대해 구매자(초보자)가 이해하기 쉽게 분석 리포트를 생성해 주세요.
            각 항목은 Markdown을 사용하여 명확하게 구분하고, 친절한 말투를 사용해 주세요.
            텍스트에서 정보를 찾을 수 없으면 "정보 없음" 또는 "특이사항 없음"으로 표시해 주세요.

            1.  **차량 기본 정보:**
                (차명, 차량번호, 연식, 주행거리를 찾아서 요약)

            2.  **사고 및 수리 이력 분석 (가장 중요):**
                (텍스트에서 '사고이력', '교환', '판금' 등의 정보를 찾아 분석. 예: '프론트 휀더(우) 교환(X)' 이력이 있습니다. 이는 주행에...)

            3.  **잠재적 리스크 및 조언 (예상 비용 포함):**
                (텍스트에서 '누유', '미세누수' 등의 정보를 찾아 분석. 예: '엔진오일팬 미세누유'가 체크되어 있습니다. 당장 수리는...)
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
            if os.path.exists(file_path):
                 os.remove(file_path)
                 print(f"임시 파일 삭제 완료: {file_path}")

@app.route("/api/recommend", methods=['POST'])
def recommend_car():
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