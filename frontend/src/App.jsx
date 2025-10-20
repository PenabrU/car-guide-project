import React, { useState } from 'react';
import './App.css'; // 기본 스타일을 위해 App.css도 가져옵니다.

function App() {
  // 백엔드에서 받아온 메시지를 저장할 변수
  const [backendMessage, setBackendMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 버튼 클릭 시 실행될 함수
  const handleApiCall = () => {
    setIsLoading(true);
    setBackendMessage('');

    // 백엔드 API(http://localhost:5000/api/greet)에 요청 보내기
    fetch('http://localhost:5000/api/greet')
      .then(response => response.json())
      .then(data => {
        // 성공적으로 데이터를 받으면 메시지를 조합해서 저장
        const message = `${data.greeting} ${data.message}`;
        setBackendMessage(message);
      })
      .catch(error => {
        // 에러 발생 시
        console.error('API 호출 에러:', error);
        setBackendMessage('서버와 통신 중 에러가 발생했습니다.');
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  return (
    <div className="App"> {/* 기본 스타일 적용을 위해 className 추가 */}
      <header className="App-header"> {/* 기본 스타일 적용 */}
        <h1>AI 중고차 구매 가이드</h1>
        <p>아래 버튼을 눌러 백엔드 서버와 통신하세요.</p>

        <button onClick={handleApiCall} disabled={isLoading}>
          {isLoading ? '통신 중...' : '백엔드에 인사하기'}
        </button>

        {/* 백엔드 메시지가 있을 경우에만 화면에 표시 */}
        {backendMessage && (
          <div style={{ marginTop: '20px', padding: '10px', border: '1px solid #ccc', borderRadius: '8px', backgroundColor: '#333' }}>
            <h3>서버 응답:</h3>
            <p>{backendMessage}</p>
          </div>
        )}
      </header>
    </div>
  );
}

export default App;