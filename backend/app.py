import os
import json
import google.generativeai as genai
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import documentai
from dotenv import load_dotenv

load_dotenv() # .env 파일 로드

# --- 1. Google Cloud (Document AI - OCR) 설정 ---
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account-key.json"
PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
LOCATION = os.getenv("GOOGLE_LOCATION")
PROCESSOR_ID = os.getenv("GOOGLE_PROCESSOR_ID")

documentai_client = documentai.DocumentProcessorServiceClient()
processor_name = documentai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

# --- 2. Google AI (Gemini - AI) 설정 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-pro') # 또는 gemini-pro

# --- 3. Flask 앱(서버) 설정 ---
app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- 4. API 엔드포인트 ---

@app.route("/", methods=['GET'])
def health_check():
    """서버 헬스 체크 API"""
    return jsonify({"status": "ok", "message": "백엔드 서버가 정상 동작 중입니다."})

@app.route("/api/upload", methods=['POST'])
def upload_file_and_analyze():
    """(기능 1) 파일 업로드, OCR 분석, Gemini 리포트(JSON) 생성을 모두 처리하는 API"""
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
            # --- Document AI (OCR) 분석 ---
            print("Document AI 분석 시작...")
            with open(file_path, "rb") as doc_file:
                doc_content = doc_file.read()
            mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "image/jpeg"
            raw_document = documentai.RawDocument(content=doc_content, mime_type=mime_type)
            request_doc = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
            result = documentai_client.process_document(request=request_doc)
            document = result.document
            ocr_full_text = document.text
            print("Document AI 분석 완료. 추출된 텍스트(뭉텅이):")
            print(ocr_full_text[:500])

            # --- Gemini AI (분석) ---
            print("Gemini AI 분석 시작...")
            prompt = f"""
            당신은 중고차 성능기록부 분석 및 시세 예측 전문가입니다. OCR 오류를 수정하고 JSON 형식으로 응답합니다.
            다음은 PDF에서 추출된 성능기록부의 '전체 텍스트'입니다:
            ---
            {ocr_full_text}
            ---

            [작업 지시]
            이 텍스트를 해석하여, 아래 JSON 형식에 맞춰 분석 리포트를 생성해 주세요.
            OCR 오류 가능성을 인지하고, 한국 차량 번호 체계에 맞게 '차량 번호'를 추론하여 수정해 주세요.
            정보를 찾을 수 없으면 해당 값에 "정보 없음" 또는 null을 사용하세요.
            **적정 시세 예측 시에는 연식, 주행거리, 사고 이력, 주요 상태(누유 등)를 종합적으로 고려해야 합니다.**

            {{
              "basicInfo": {{
                "modelName": "차명 (예: 아반떼 AD)",
                "carNumber": "차량번호 (수정된 번호)",
                "year": "연식 (예: 2016년)",
                "mileage": "주행거리 (예: 130,830km)"
              }},
              "accidentHistory": {{
                "summary": "사고 이력 요약 (예: 단순 수리 2건(우측 휀더, 도어 교환), 주요 골격 손상 없음)",
                "details": [
                  "상세 설명 1 (예: 프론트 휀더(우) 교환(X): 경미한 외부 패널 교체로 주행 성능 영향 없음)",
                  "상세 설명 2 (예: 프론트 도어(우) 교환(X): 동일)"
                ]
              }},
              "risksAndAdvice": {{
                "summary": "잠재적 리스크 요약 (예: 엔진오일 미세누유 1건 발견, 즉시 수리 불필요)",
                "details": [
                  {{
                    "item": "엔진오일팬",
                    "status": "미세누유",
                    "advice": "당장 수리는 필요 없으나, 1~2년 내 가스켓 교환 필요 가능성 있음.",
                    "estimatedCost": "약 15~25만 원"
                  }}
                ],
                "priceGuidance": "가격 협상 가이드 (예: 사고 이력 2건과 미세누유 1건을 고려할 때, 시세 대비 약 50~80만 원 정도의 감가 요인이 있을 수 있습니다. 구매 시 가격 협상을 시도해 보세요.)"
              }},
              "predictedPrice": {{
                "range": "AI 예측 적정 시세 범위 (예: 1850만원 ~ 2050만원)",
                "basis": "예측 근거 요약 (예: 주행거리는 다소 많지만 주요 골격 사고가 없고 관리가 잘 된 점을 고려했습니다. 다만, 미세누유 수리 비용은 감안해야 합니다.)"
              }}
            }}
            """
            generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
            response = gemini_model.generate_content(prompt, generation_config=generation_config)

            analysis_result_json = {}
            status_code = 500
            try:
                analysis_result_json = json.loads(response.text)
                print("Gemini AI 분석 완료 (JSON).")
                status_code = 200
            except json.JSONDecodeError:
                print("Gemini AI가 유효한 JSON을 반환하지 못했습니다. 텍스트로 대체합니다.")
                analysis_result_json = {"error": "AI가 분석 결과를 생성하는 데 실패했습니다.", "raw_text": response.text}
            except Exception as inner_e:
                 print(f"Gemini 응답 처리 중 오류: {inner_e}")
                 analysis_result_json = {"error": "AI 응답 처리 중 오류 발생"}


            return jsonify({
                "status": "success" if status_code == 200 else "error",
                "message": f"'{filename}' 파일 분석 " + ("성공!" if status_code == 200 else "실패."),
                "data": analysis_result_json
            }), status_code

        except Exception as e:
            print(f"AI 분석 중 오류 발생: {e}")
            return jsonify({"status": "error", "message": f"AI 분석 중 오류가 발생했습니다: {e}"}), 500

        finally:
            if os.path.exists(file_path):
                 os.remove(file_path)
                 print(f"임시 파일 삭제 완료: {file_path}")

@app.route("/api/recommend", methods=['POST'])
def recommend_car():
    """(기능 2) AI 차량 추천 API (JSON 응답)"""
    data = request.json
    if not data or 'lifestyle_text' not in data:
        return jsonify({"status": "error", "message": "요청 내용이 없습니다."}), 400

    user_text = data['lifestyle_text']
    print(f"사용자 요청 텍스트: {user_text}")

    try:
        prompt = f"""
        당신은 중고차 추천 전문 컨설턴트입니다. 사용자의 요구사항을 분석하여 최적의 중고차 모델 3가지를 JSON 형식으로 추천합니다.
        사용자 요청:
        ---
        "{user_text}"
        ---

        [작업 지시]
        사용자의 예산, 나이, 가족 구성, 주 용도, 선호 스타일 뿐만 아니라, **연비, 유지보수 용이성, 안전 등급**과 같은 현실적인 요소도 고려하여 추천해 주세요.
        아래 JSON 형식을 정확히 지켜서, 각 추천 모델에 대한 이유와 예상 시세를 포함하여 생성해 주세요.

        {{
          "recommendations": [
            {{
              "rank": 1,
              "modelName": "추천 모델 1 (예: 싼타페 TM)",
              "reason": "추천 이유 (예: 30대 가족의 패밀리카로 가장 무난하며, 캠핑용 짐을 싣기 좋고 연비도 준수합니다.)",
              "priceRange": "예상 시세 (예: 2000~2500만 원)"
            }},
            {{
              "rank": 2,
              "modelName": "추천 모델 2 (예: 기아 쏘렌토 4세대)",
              "reason": "추천 이유",
              "priceRange": "예상 시세"
            }},
            {{
              "rank": 3,
              "modelName": "추천 모델 3 (예: 르노 QM6)",
              "reason": "추천 이유",
              "priceRange": "예상 시세"
            }}
          ]
        }}
        """

        print("Gemini AI 추천 시작...")
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        response = gemini_model.generate_content(prompt, generation_config=generation_config)

        recommendation_result_json = {}
        status_code = 500
        try:
            recommendation_result_json = json.loads(response.text)
            print("Gemini AI 추천 완료 (JSON).")
            status_code = 200
        except json.JSONDecodeError:
            print("Gemini AI가 유효한 JSON 추천 결과를 반환하지 못했습니다.")
            recommendation_result_json = {"error": "AI가 추천 결과를 생성하는 데 실패했습니다.", "raw_text": response.text}
        except Exception as inner_e:
             print(f"Gemini 응답 처리 중 오류: {inner_e}")
             recommendation_result_json = {"error": "AI 응답 처리 중 오류 발생"}


        return jsonify({
            "status": "success" if status_code == 200 else "error",
            "message": "차량 추천 " + ("성공!" if status_code == 200 else "실패."),
            "data": recommendation_result_json
        }), status_code

    except Exception as e:
        print(f"AI 추천 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": "AI 추천 중 오류가 발생했습니다."}), 500

@app.route("/api/ask-report", methods=['POST'])
def ask_report_chatbot():
    """(기능 3 - 11단계) 분석 리포트 Q&A 챗봇 API"""
    data = request.json
    if not data or 'report_data' not in data or 'user_question' not in data:
        return jsonify({"status": "error", "message": "리포트 내용 또는 질문이 없습니다."}), 400

    report_context = data['report_data']
    user_question = data['user_question']

    # report_context가 객체 형태일 경우 JSON 문자열로 변환
    if isinstance(report_context, dict):
        report_text = json.dumps(report_context, ensure_ascii=False, indent=2)
    else:
        report_text = report_context # 이미 텍스트 형태인 경우

    print(f"리포트 컨텍스트 길이: {len(report_text)} 자")
    print(f"사용자 질문: {user_question}")

    try:
        prompt = f"""
        당신은 AI 중고차 분석가입니다. 사용자가 이전에 생성된 분석 리포트에 대해 질문하고 있습니다.
        주어진 리포트 내용을 바탕으로 사용자의 질문에 간결하고 명확하게 답변해 주세요.

        [분석 리포트 내용]
        ---
        {report_text}
        ---

        [사용자 질문]
        "{user_question}"

        [답변 가이드라인]
        - 반드시 주어진 [분석 리포트 내용] 안에서만 정보를 찾아서 답변해야 합니다.
        - 리포트에 없는 내용을 추측하거나 외부 지식을 사용하지 마세요.
        - 질문이 리포트 내용과 관련 없거나 답변할 수 없으면, "리포트 내용으로는 답변하기 어려운 질문입니다." 라고 솔직하게 말해주세요.
        - 친절하고 이해하기 쉬운 말투로 답변해 주세요.

        [AI 답변]
        """

        print("Gemini AI 답변 생성 시작...")
        response = gemini_model.generate_content(prompt)
        ai_answer = response.text
        print("Gemini AI 답변 생성 완료.")

        return jsonify({
            "status": "success",
            "message": "AI 답변 생성 성공!",
            "data": ai_answer
        })

    except Exception as e:
        print(f"AI 답변 생성 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": "AI 답변 생성 중 오류가 발생했습니다."}), 500

# --- 5. Flask 서버 실행 ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)