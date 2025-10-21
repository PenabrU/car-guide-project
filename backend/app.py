import os
import json
import re # 정규표현식 라이브러리 임포트
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
CORS(app) # 모든 외부 요청 허용
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- 차량 번호 검사 및 수정 함수 (강화 버전) ---
def correct_car_number_format(text):
    """
    OCR 텍스트에서 '차량번호' 뒤 7자리 숫자 패턴을 찾아 '2'를 '오'로 수정 시도.
    """
    corrected_text = text # 원본 텍스트 복사
    pattern = r"(?:차량번호|차량 번호)\s*(\d{7})" # '차량번호' 뒤 7자리 숫자
    match = re.search(pattern, text)

    if match:
        original_number = match.group(1) # 7자리 숫자 부분
        print(f"정규표현식 매치 성공: 키워드 근처에서 '{original_number}' 발견")

        # 패턴이 '612'로 시작하고 총 7자리 숫자인 경우 (오류 가능성 높음)
        if original_number.startswith("612") and len(original_number) == 7:
            suffix = original_number[3:] # 마지막 4자리 숫자
            corrected_number = f"61오{suffix}" # '61오' + 나머지 4자리
            print(f"차량 번호 형식 오류 감지 및 수정 시도: {original_number} -> {corrected_number}")
            original_pattern_in_text = match.group(0)
            keyword_part = original_pattern_in_text.replace(original_number, "")
            corrected_pattern_in_text = f"{keyword_part}{corrected_number}"
            corrected_text = text.replace(original_pattern_in_text, corrected_pattern_in_text, 1)
            print(f"텍스트 교체 시도: '{original_pattern_in_text}' -> '{corrected_pattern_in_text}'")
        else:
            print(f"발견된 번호 '{original_number}'는 수정 조건(612xxxx)에 맞지 않아 수정하지 않음.")
    else:
        print("텍스트에서 '차량번호 + 7자리 숫자' 패턴을 찾지 못함.")

    return corrected_text
# --- [여기까지 함수 추가] ---


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

            # --- 차량 번호 형식 검사 및 수정 ---
            print("차량 번호 형식 검사 및 수정 시도...")
            corrected_ocr_text = correct_car_number_format(ocr_full_text)

            # --- Gemini AI (분석) ---
            print("Gemini AI 분석 시작...")
            # [상세 설명 요청!] Gemini 프롬프트 수정
            prompt = f"""
            당신은 중고차 성능기록부 분석, 시세 예측, 유지보수 예측, 그리고 위험도 평가 전문가입니다. OCR 오류를 수정하고 **상세한** JSON 형식으로 응답합니다.
            다음은 PDF에서 추출되고 일부 오류가 '사전 수정된' 성능기록부의 '전체 텍스트'입니다:
            ---
            {corrected_ocr_text}
            ---

            [작업 지시]
            이 텍스트를 **꼼꼼히 해석**하여, 아래 JSON 형식에 맞춰 **가능한 모든 관련 정보를 포함하여 상세하게** 분석 리포트를 생성해 주세요.
            [매우 중요!] '차량 번호'는 주어진 텍스트에 있는 값을 '절대로' 변경하지 말고 그대로 사용해야 합니다.
            정보를 찾을 수 없으면 해당 값에 "정보 없음" 또는 null을 사용하세요.
            **사고 이력과 리스크 항목은 발견된 모든 내용을 누락 없이 상세히 기술해주세요.**
            **적정 시세 예측 시에는 연식, 주행거리, 사고 이력, 주요 상태(누유 등)를 종합적으로 고려해야 합니다.**
            **유지보수 예측 시에는 차명, 연식, 주행거리를 바탕으로 일반적인 교체 주기와 해당 차종의 알려진 고질병을 고려해야 합니다.**
            **위험도 점수는 0점(매우 위험)부터 100점(매우 안전) 사이의 정수로 평가하고, 주요 평가 근거를 요약해서 제시해야 합니다.** 사고 이력, 주행거리, 누유/누수 등을 종합적으로 고려하세요.

            {{
              "basicInfo": {{
                "modelName": "차명", "carNumber": "차량번호", "year": "연식", "mileage": "주행거리"
              }},
              "accidentHistory": {{
                "summary": "사고 이력 요약 (발견된 모든 교환(X), 판금(W) 부위를 명시하고, 주요 골격 손상 여부 반드시 언급, 없으면 '없음')",
                "details": [
                    "상세 설명 1 (각 부위별 상태, 수리 종류(X/W), 의미를 구체적으로 작성)",
                    "상세 설명 2 (...)"
                 ]
              }},
              "risksAndAdvice": {{
                "summary": "현재 잠재적 리스크 요약 (발견된 모든 누유, 누수, 부식 등 상태 언급, 없으면 '특이사항 없음')",
                "details": [
                    {{ "item": "항목명", "status": "상태 (미세누유, 누유 등)", "advice": "구체적인 조언 (예: 당장 수리 필요 여부, 장기적 영향)", "estimatedCost": "예상 비용 (범위로 제시)" }}
                    // 발견된 모든 리스크 항목을 여기에 추가
                 ],
                "priceGuidance": "현재 가격 협상 가이드 (분석된 모든 특이사항을 고려하여 구체적인 감가 요인 언급)"
              }},
              "predictedPrice": {{
                "range": "AI 예측 적정 시세 범위",
                "basis": "현재 상태 기반 예측 근거 (주행거리, 사고 이력, 리스크 항목 등을 구체적으로 언급하며 설명)"
              }},
              "maintenancePrediction": {{
                "majorItems": [ // 주요 정비 항목 상세화
                  {{ "item": "예상 정비 항목", "timing": "예상 시기 (주행거리 또는 기간)", "estimatedCost": "예상 비용 (범위)" }},
                  {{ "item": "...", "timing": "...", "estimatedCost": "..." }}
                ],
                "commonIssues": [ // 고질병 정보 상세화
                   "고질병 1 (구체적인 증상이나 원인 포함)",
                   "고질병 2 (...)"
                 ],
                "overallAdvice": "종합 유지보수 조언 (차량 상태와 주행거리를 고려한 현실적인 조언)"
              }},
              "riskScore": {{
                "score": "위험도 점수 (0~100 정수)",
                "summary": "평가 근거 요약 (점수에 영향을 미친 주요 항목들을 구체적으로 언급)"
              }}
            }}
            """
            generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
            response = gemini_model.generate_content(prompt, generation_config=generation_config)

            analysis_result_json = {}
            status_code = 500
            try:
                cleaned_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
                analysis_result_json = json.loads(cleaned_text)
                # --- [추가!] Gemini가 반환한 JSON 내용 출력 ---
                print("--- Gemini가 반환한 JSON ---")
                print(json.dumps(analysis_result_json, indent=2, ensure_ascii=False)) # 예쁘게 출력
                print("--------------------------")
                # --- [여기까지 추가] ---
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
    # ... (이전과 동일) ...
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
            {{ "rank": 1, "modelName": "모델1", "reason": "이유1", "priceRange": "시세1" }},
            {{ "rank": 2, "modelName": "모델2", "reason": "이유2", "priceRange": "시세2" }},
            {{ "rank": 3, "modelName": "모델3", "reason": "이유3", "priceRange": "시세3" }}
          ]
        }}
        """
        print("Gemini AI 추천 시작...")
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        response = gemini_model.generate_content(prompt, generation_config=generation_config)
        recommendation_result_json = {}
        status_code = 500
        try:
            cleaned_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            recommendation_result_json = json.loads(cleaned_text)
            print("Gemini AI 추천 완료 (JSON).")
            status_code = 200
        except json.JSONDecodeError:
             print("Gemini AI가 유효한 JSON 추천 결과를 반환하지 못했습니다.")
             recommendation_result_json = {"error": "AI가 추천 결과를 생성하는 데 실패했습니다.", "raw_text": response.text}
        except Exception as inner_e:
             print(f"Gemini 응답 처리 중 오류: {inner_e}")
             recommendation_result_json = {"error": "AI 응답 처리 중 오류 발생"}
        return jsonify({"status": "success" if status_code == 200 else "error", "message": "차량 추천 " + ("성공!" if status_code == 200 else "실패."), "data": recommendation_result_json}), status_code
    except Exception as e:
        print(f"AI 추천 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": "AI 추천 중 오류가 발생했습니다."}), 500


@app.route("/api/ask-report", methods=['POST'])
def ask_report_chatbot():
    """(기능 3) 분석 리포트 Q&A 챗봇 API"""
    # ... (이전과 동일) ...
    data = request.json
    if not data or 'report_data' not in data or 'user_question' not in data:
        return jsonify({"status": "error", "message": "리포트 내용 또는 질문이 없습니다."}), 400
    report_context = data['report_data']
    user_question = data['user_question']
    if isinstance(report_context, dict):
        report_text = json.dumps(report_context, ensure_ascii=False, indent=2)
    else: report_text = report_context
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
        # --- [FIX!] Added missing return statement ---
        return jsonify({
            "status": "success",
            "message": "AI 답변 생성 성공!",
            "data": ai_answer # The AI's textual answer
        })
        # --- [End Fix] ---
    except Exception as e:
        print(f"AI 답변 생성 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": "AI 답변 생성 중 오류가 발생했습니다."}), 500


# --- 5. Flask 서버 실행 ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)