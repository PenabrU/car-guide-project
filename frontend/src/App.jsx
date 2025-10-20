import React, { useState } from 'react';
import './App.css'; // 수정된 App.css를 가져옵니다.

function App() {
  // 기능 1: 성능기록부 분석
  const [backendMessage, setBackendMessage] = useState(null); 
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  // 기능 2: 맞춤 차량 추천
  const [lifestyleText, setLifestyleText] = useState(''); // 사용자가 입력할 텍스트
  const [recommendLoading, setRecommendLoading] = useState(false); // 추천 로딩
  const [recommendResult, setRecommendResult] = useState(null); // 추천 결과

  // --- (기능 1) 파일 선택 시 ---
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setBackendMessage(null); // 파일이 바뀌면 이전 메시지 초기화
    }
  };

  // --- (기능 1) 분석 버튼 클릭 시 ---
  const handleUpload = () => {
    if (!selectedFile) {
      setBackendMessage({ 
        status: "error", 
        message: "파일을 먼저 선택해주세요." 
      });
      return;
    }

    setIsLoading(true);
    setBackendMessage(null);
    const formData = new FormData();
    formData.append('file', selectedFile);

    fetch('http://localhost:5000/api/upload', {
      method: 'POST',
      body: formData,
    })
      .then(response => response.json())
      .then(data => {
        setBackendMessage(data); // 백엔드 응답(data)을 통째로 저장
      })
      .catch(error => {
        console.error('업로드 에러:', error);
        setBackendMessage({ 
          status: "error", 
          message: "서버와 통신 중 에러가 발생했습니다." 
        });
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  // --- (기능 2) 추천 버튼 클릭 시 ---
  const handleRecommend = () => {
    if (!lifestyleText) {
      setRecommendResult({ 
        status: "error", 
        message: "원하는 차량의 조건을 입력해주세요." 
      });
      return;
    }

    setRecommendLoading(true);
    setRecommendResult(null);

    // 백엔드 /api/recommend 주소로 텍스트 전송
    fetch('http://localhost:5000/api/recommend', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json', // 텍스트(json)를 보낸다고 알림
      },
      body: JSON.stringify({
        lifestyle_text: lifestyleText // 백엔드가 받을 key 이름과 맞춤
      }),
    })
      .then(response => response.json())
      .then(data => {
        setRecommendResult(data); // 백엔드 응답(data)을 통째로 저장
      })
      .catch(error => {
        console.error('추천 에러:', error);
        setRecommendResult({ 
          status: "error", 
          message: "서버와 통신 중 에러가 발생했습니다." 
        });
      })
      .finally(() => {
        setRecommendLoading(false);
      });
  };

  // --- 화면에 보이는 HTML 부분 ---
  return (
    <div className="App">
      <header className="App-header">
        <h1>AI 중고차 구매 가이드</h1>
      </header>

      <main>
        {/* --- 1. 성능기록부 분석 섹션 --- */}
        <section className="feature-section">
          <h2>1. 성능기록부 분석하기</h2>
          <p>PDF/이미지를 업로드하여 잠재적 리스크와 가치를 확인하세요.</p>
          <div className="upload-section">
            <label htmlFor="file-upload" className="file-label">
              파일 선택하기
            </label>
            <input 
              id="file-upload"
              type="file" 
              onChange={handleFileChange} 
              accept="application/pdf, image/png, image/jpeg"
            />
            {selectedFile && (
              <p className="file-name">{selectedFile.name}</p>
            )}
            <button 
              onClick={handleUpload} 
              disabled={isLoading || !selectedFile}
              className="upload-button"
            >
              {isLoading ? '분석 중...' : '업로드 및 분석'}
            </button>
          </div>
          {/* 분석 결과 표시 */}
          {backendMessage && (
            <div className="result-section">
              <h3 style={{ color: backendMessage.status === 'error' ? 'red' : 'green' }}>
                {backendMessage.status === 'success' ? '✅ AI 분석 리포트' : '🚨 오류 발생'}
              </h3>
              {backendMessage.data ? 
                (<pre className="analysis-text">{backendMessage.data}</pre>) :
                (<p>{backendMessage.message}</p>)
              }
            </div>
          )}
        </section>

        {/* --- 2. 맞춤 차량 추천 섹션 --- */}
        <section className="feature-section">
          <h2>2. AI 맞춤 차량 추천받기</h2>
          <p>예산, 용도, 라이프스타일을 알려주시면 AI가 최적의 차량을 추천해 드립니다.</p>
          
          <textarea
            className="lifestyle-textarea"
            placeholder="예시: 30대 직장인이고, 주말엔 캠핑을 즐깁니다. 예산은 2천만원입니다. 안전하고 튼튼한 SUV를 원해요."
            value={lifestyleText}
            onChange={(e) => setLifestyleText(e.target.value)}
          />

          <button 
            onClick={handleRecommend} 
            disabled={recommendLoading}
            className="upload-button recommend-button" // recommend-button 클래스 추가
          >
            {recommendLoading ? '추천 찾는 중...' : 'AI에게 추천받기'}
          </button>
          
          {/* 추천 결과 표시 */}
          {recommendResult && (
            <div className="result-section">
              <h3 style={{ color: recommendResult.status === 'error' ? 'red' : 'green' }}>
                {recommendResult.status === 'success' ? '✅ AI 맞춤 추천 리스트' : '🚨 오류 발생'}
              </h3>
              {recommendResult.data ? 
                (<pre className="analysis-text">{recommendResult.data}</pre>) :
                (<p>{recommendResult.message}</p>)
              }
            </div>
          )}
        </section>

      </main>
    </div>
  );
}

export default App;