import React, { useState, useRef, useEffect } from 'react'; // useRef, useEffect 추가
import './App.css';
import AnalysisReport from './components/AnalysisReport';
import RecommendationList from './components/RecommendationList';

function App() {
  // --- State Variables ---
  const [backendMessage, setBackendMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [lifestyleText, setLifestyleText] = useState('');
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [recommendResult, setRecommendResult] = useState(null);
  const [userQuestion, setUserQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);

  // --- Refs ---
  const chatHistoryRef = useRef(null); // 채팅 스크롤을 위한 Ref

  // --- Effects ---
  // 채팅 메시지가 추가될 때마다 맨 아래로 스크롤
  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [chatHistory]);

  // --- Event Handlers ---
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setBackendMessage(null);
      setChatHistory([]); // 새 파일 선택 시 채팅 기록 초기화
    }
  };

  const handleUpload = () => {
    if (!selectedFile) {
      setBackendMessage({ status: "error", message: "파일을 먼저 선택해주세요." });
      return;
    }
    setIsLoading(true);
    setBackendMessage(null);
    setChatHistory([]); // 분석 시작 시 채팅 기록 초기화
    const formData = new FormData();
    formData.append('file', selectedFile);

    fetch('http://localhost:5000/api/upload', { method: 'POST', body: formData })
      .then(response => response.json())
      .then(data => { setBackendMessage(data); })
      .catch(error => {
        console.error('업로드 에러:', error);
        setBackendMessage({ status: "error", message: "서버와 통신 중 에러가 발생했습니다." });
      })
      .finally(() => { setIsLoading(false); });
  };

  const handleRecommend = () => {
    if (!lifestyleText) {
      setRecommendResult({ status: "error", message: "원하는 차량의 조건을 입력해주세요." });
      return;
    }
    setRecommendLoading(true);
    setRecommendResult(null);

    fetch('http://localhost:5000/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lifestyle_text: lifestyleText }),
    })
      .then(response => response.json())
      .then(data => { setRecommendResult(data); })
      .catch(error => {
        console.error('추천 에러:', error);
        setRecommendResult({ status: "error", message: "서버와 통신 중 에러가 발생했습니다." });
      })
      .finally(() => { setRecommendLoading(false); });
  };

  const handleAskChatbot = () => {
    if (!userQuestion || !backendMessage || backendMessage.status !== 'success' || !backendMessage.data) {
      alert('분석 리포트가 성공적으로 생성된 후 질문을 입력해주세요.');
      return;
    }

    setChatLoading(true);
    const currentReportData = backendMessage.data;
    const questionToSend = userQuestion; // 현재 질문 저장
    setUserQuestion(''); // 입력창 먼저 비우기

    // 사용자 질문을 채팅 기록에 먼저 추가
    setChatHistory(prev => [...prev, { type: 'user', text: questionToSend }]);

    fetch('http://localhost:5000/api/ask-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        report_data: currentReportData,
        user_question: questionToSend
      }),
    })
      .then(response => response.json())
      .then(data => {
        setChatHistory(prev => [
          ...prev,
          { type: 'ai', text: data.data || data.message }
        ]);
      })
      .catch(error => {
        console.error('챗봇 에러:', error);
        setChatHistory(prev => [
          ...prev,
          { type: 'ai', text: '죄송합니다. 답변 생성 중 오류가 발생했습니다.' }
        ]);
      })
      .finally(() => {
        setChatLoading(false);
      });
  };

  // --- Render ---
  return (
    <div>
      <header className="App-hero">
        <h1>AI 중고차 구매 가이드</h1>
        <p className="App-subtitle">복잡한 중고차 구매, AI 전문가와 함께 쉽고 안전하게!</p>
      </header>
      <main>
        {/* Analysis Card */}
        <section className="feature-card">
          <h2><span className="card-icon">📄</span>성능기록부 AI 분석</h2>
          <p className="card-description">PDF/이미지를 업로드하면 AI가 숨겨진 리스크와 적정 가치를 분석해 드립니다.</p>
          <div className="upload-section">
            <label htmlFor="file-upload" className="file-label">
              {selectedFile ? '파일 변경' : '파일 선택하기'}
            </label>
            <input id="file-upload" type="file" onChange={handleFileChange} accept="application/pdf, image/png, image/jpeg"/>
            {selectedFile && (<p className="file-name">{selectedFile.name}</p>)}
          </div>
          <button onClick={handleUpload} disabled={isLoading || !selectedFile} className="action-button analysis-button">
            {isLoading ? (<><span className="loading-spinner"></span> 분석 중...</>) : ('결과 분석하기')}
          </button>
          {/* Analysis Result Display */}
          {backendMessage && (
            <div className="result-section">
              <h3>
                <span className="icon">{backendMessage.status === 'success' ? '✅' : '🚨'}</span>
                {backendMessage.status === 'success' ? 'AI 분석 리포트' : '오류 발생'}
              </h3>
              <AnalysisReport analysisData={backendMessage.data} />
              {backendMessage.status === 'error' && (!backendMessage.data || typeof backendMessage.data !== 'object' || !backendMessage.data.error) && (
                <p>{backendMessage.message}</p>
              )}

              {/* Q&A Chatbot UI */}
              {backendMessage.status === 'success' && backendMessage.data && !backendMessage.data.error && (
                <div className="chatbot-section">
                  <h4>💬 리포트 내용 질문하기</h4>
                  <div className="chat-history" ref={chatHistoryRef}> {/* Ref 추가 */}
                    {chatHistory.map((msg, index) => (
                      <div key={index} className={`chat-message ${msg.type}`}>
                         {msg.text} {/* Prefix 제거 */}
                      </div>
                    ))}
                    {chatLoading && <div className="chat-message ai loading"><span></span><span></span><span></span></div>} {/* 로딩 애니메이션 */}
                  </div>
                  <div className="chat-input-area">
                    <input
                      type="text"
                      className="chat-input"
                      placeholder="예: 엔진오일 누유 심각한가요?"
                      value={userQuestion}
                      onChange={(e) => setUserQuestion(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && !chatLoading && handleAskChatbot()}
                    />
                    <button onClick={handleAskChatbot} disabled={chatLoading || !userQuestion} className="chat-button">
                      질문 전송
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Recommendation Card */}
        <section className="feature-card">
          <h2><span className="card-icon">🚗</span>AI 맞춤 차량 추천</h2>
          <p className="card-description">예산, 용도, 라이프스타일을 알려주시면 AI가 최적의 중고차를 찾아드립니다.</p>
           <textarea
             className="lifestyle-textarea"
             placeholder="예시: 30대 직장인이고, 주말엔 캠핑을 즐깁니다. 예산은 2천만원입니다. 안전하고 튼튼한 SUV를 원해요."
             value={lifestyleText}
             onChange={(e) => setLifestyleText(e.target.value)}
           />
           <button onClick={handleRecommend} disabled={recommendLoading} className="action-button recommend-button">
             {recommendLoading ? (<><span className="loading-spinner"></span> 추천 찾는 중...</>) : ('AI에게 추천받기')}
           </button>
          {recommendResult && (
            <div className="result-section">
              <h3>
                <span className="icon">{recommendResult.status === 'success' ? '✅' : '🚨'}</span>
                {recommendResult.status === 'success' ? 'AI 맞춤 추천 리스트' : '오류 발생'}
              </h3>
              <RecommendationList recommendData={recommendResult.data} />
              {recommendResult.status === 'error' && (!recommendResult.data || typeof recommendResult.data !== 'object' || !recommendResult.data.error) && (
                <p>{recommendResult.message}</p>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;