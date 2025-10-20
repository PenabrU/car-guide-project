from flask import Flask, jsonify
from flask_cors import CORS  # 1. CORS 임포트

app = Flask(__name__)
CORS(app)  # 2. 앱에 CORS 적용 (이제 다른 주소 요청 허용)

@app.route("/", methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "AI 중고차 구매 가이드 백엔드 서버가 정상적으로 동작 중입니다!"
    })

# 3. [새 API 추가] 프론트엔드로 보낼 데이터를 정의
@app.route("/api/greet", methods=['GET'])
def greet():
    """프론트엔드의 요청에 응답하는 테스트 API"""
    response_data = {
        "greeting": "안녕하세요!",
        "message": "AI 중고차 구매 가이드 백엔드 서버입니다."
    }
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)