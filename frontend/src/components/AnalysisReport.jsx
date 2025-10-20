import React from 'react';
import './AnalysisReport.css'; // 전용 CSS 파일 임포트

function AnalysisReport({ analysisData }) {
  // 데이터가 없거나 객체가 아니면 표시 안 함
  if (!analysisData || typeof analysisData !== 'object') {
     return <p className="no-results">분석 데이터를 표시할 수 없습니다.</p>;
  }

  // Gemini가 JSON 생성에 실패했을 경우
  if (analysisData.error) {
    return (
      <div className="error-box">
        <p style={{ color: 'red' }}><strong>오류:</strong> {analysisData.error}</p>
        <p><strong>Raw Response:</strong></p>
        <pre className="raw-text">{analysisData.raw_text || 'No raw text available.'}</pre>
      </div>
    );
  }

  // 데이터 추출 (시세 예측 포함)
  const { basicInfo, accidentHistory, risksAndAdvice, predictedPrice } = analysisData;

  // Render nothing if all data sections are potentially missing or empty
  if (!basicInfo && !accidentHistory && !risksAndAdvice && !predictedPrice) {
      return <p className="no-results">분석된 내용이 없습니다.</p>;
  }

  return (
    <div className="analysis-report">
      {basicInfo && (
        <div className="report-section">
          <h4>📋 차량 기본 정보</h4>
          <div className="info-grid">
            <span>차명:</span> <strong>{basicInfo.modelName || '정보 없음'}</strong>
            <span>차량번호:</span> <strong>{basicInfo.carNumber || '정보 없음'}</strong>
            <span>연식:</span> <strong>{basicInfo.year || '정보 없음'}</strong>
            <span>주행거리:</span> <strong>{basicInfo.mileage || '정보 없음'}</strong>
          </div>
        </div>
      )}
      {accidentHistory && (
        <div className="report-section">
          <h4>💥 사고 및 수리 이력 분석</h4>
          <p className="summary">{accidentHistory.summary || '특이사항 없음'}</p>
          {accidentHistory.details && accidentHistory.details.length > 0 && (
            <ul className="details-list">
              {accidentHistory.details.map((detail, index) => (
                <li key={index}>{detail}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {risksAndAdvice && (
        <div className="report-section">
          <h4>⚠️ 잠재적 리스크 및 조언</h4>
          <p className="summary">{risksAndAdvice.summary || '특이사항 없음'}</p>
          {risksAndAdvice.details && risksAndAdvice.details.length > 0 && (
            <ul className="details-list risk-list">
              {risksAndAdvice.details.map((item, index) => (
                <li key={index}>
                  <span className="item-label">{item.item}:</span>
                  <span className="item-status">{item.status}</span>
                  <span className="item-advice">{item.advice}</span>
                  <span className="item-cost">(예상 비용: {item.estimatedCost})</span>
                </li>
              ))}
            </ul>
          )}
          <p className="price-guidance"><strong>가격 가이드:</strong> {risksAndAdvice.priceGuidance || '정보 없음'}</p>
        </div>
      )}
      {/* AI 예측 시세 섹션 */}
      {predictedPrice && (
        <div className="report-section price-section">
          <h4>💰 AI 예측 적정 시세</h4>
          <p className="predicted-range">{predictedPrice.range || '정보 없음'}</p>
          <p className="prediction-basis"><strong>예측 근거:</strong> {predictedPrice.basis || '정보 없음'}</p>
        </div>
      )}
    </div>
  );
}

export default AnalysisReport;