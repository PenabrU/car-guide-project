// frontend/src/components/AnalysisReport.jsx (useState import 수정됨)
import React, { useState } from 'react'; // useState 임포트 확인!
import './AnalysisReport.css';
import TermModal from './TermModal';

function AnalysisReport({ analysisData }) {
  // 모달 상태 관리
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTerm, setModalTerm] = useState('');
  const [modalExplanation, setModalExplanation] = useState('');
  const [modalLoading, setModalLoading] = useState(false);

  // 데이터 유효성 검사
  if (!analysisData || typeof analysisData !== 'object') {
     return <p className="no-results">분석 데이터를 표시할 수 없습니다.</p>;
  }

  // Gemini JSON 생성 실패 시
  if (analysisData.error) {
    return (
      <div className="error-box">
        <p style={{ color: 'red' }}><strong>오류:</strong> {analysisData.error}</p>
        <p><strong>Raw Response:</strong></p>
        <pre className="raw-text">{analysisData.raw_text || 'No raw text available.'}</pre>
      </div>
    );
  }

  // 모든 데이터 섹션 추출
  const { basicInfo, accidentHistory, risksAndAdvice, predictedPrice, maintenancePrediction, riskScore } = analysisData;

  // 표시할 데이터가 전혀 없는 경우
  if (!basicInfo && !accidentHistory && !risksAndAdvice && !predictedPrice && !maintenancePrediction && !riskScore) {
      return <p className="no-results">분석된 내용이 없습니다.</p>;
  }

  // 점수에 따른 색상 결정 함수
  const getScoreColor = (scoreStr) => {
    const score = parseInt(scoreStr);
    if (isNaN(score)) return '#6c757d';
    if (score >= 80) return '#28a745';
    if (score >= 60) return '#ffc107';
    return '#dc3545';
  };

  // 용어 설명 요청 함수
  const handleTermClick = async (term) => {
    setModalTerm(term);
    setModalExplanation('');
    setModalLoading(true);
    setModalOpen(true);

    try {
      const response = await fetch('http://localhost:5000/api/explain-term', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term: term }),
      });
      const data = await response.json();
      setModalExplanation(data.data || data.message || '설명을 가져오는 데 실패했습니다.');
    } catch (error) {
      console.error('용어 설명 에러:', error);
      setModalExplanation('서버와 통신 중 오류가 발생했습니다.');
    } finally {
      setModalLoading(false);
    }
  };

  // 설명 대상 용어 목록
  const explainableTerms = ["미세누유", "누유", "판금", "용접", "교환", "부식", "침수", "주요 골격", "DPF", "DCT", "MDPS"];

  // 텍스트 내 용어 감지 및 아이콘 추가 함수
  const renderTextWithExplanation = (text) => {
    if (!text) return { __html: text }; // 텍스트 없으면 그대로 반환

    let processedText = text;
    explainableTerms.forEach(term => {
      const regex = new RegExp(`\\b(${term})\\b`, 'g');
      // 이미 span 태그로 감싸진 경우는 제외 (중복 방지)
      processedText = processedText.replace(regex, (match, p1, offset, string) => {
         // 이미 처리된 태그 내부에 있는지 간단히 확인
         const prevChar = string[offset - 1];
         const nextChar = string[offset + match.length];
         if (prevChar === '>' || nextChar === '<' || (string[offset - 2] === '"' && string[offset-1] === '>')) { // 간단한 태그 내부 체크
             return match; // 이미 태그 안에 있거나 속성 값이면 변경 안 함
         }
         return `<span class="explainable-term" data-term="${match}">${match}<span class="explain-icon">❓</span></span>`;
      });
    });
    return { __html: processedText };
  };


  return (
    // 클릭 이벤트 핸들러 추가
    <div className="analysis-report" onClick={(e) => {
      const target = e.target.closest('.explainable-term');
      if (target) {
        handleTermClick(target.dataset.term);
      }
    }}>
      {/* AI 위험도 점수 */}
      {riskScore && (
        <div className="report-section risk-score-section">
          <h4>💯 AI 위험도 평가</h4>
          <div className="score-display">
            <span className="score-value" style={{ color: getScoreColor(riskScore.score) }}>
              {riskScore.score || '?'}
            </span>
            <span className="score-unit"> / 100점</span>
          </div>
          <p className="score-summary"><strong>평가 근거:</strong> {riskScore.summary || '정보 없음'}</p>
        </div>
      )}

      {/* 차량 기본 정보 */}
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
      {/* 사고 및 수리 이력 */}
      {accidentHistory && (
        <div className="report-section">
          <h4>💥 사고 및 수리 이력 분석</h4>
          <p className="summary" dangerouslySetInnerHTML={renderTextWithExplanation(accidentHistory.summary)}></p>
          {accidentHistory.details && accidentHistory.details.length > 0 && (
            <ul className="details-list">
              {accidentHistory.details.map((detail, index) => (
                <li key={index} dangerouslySetInnerHTML={renderTextWithExplanation(detail)}></li>
              ))}
            </ul>
          )}
        </div>
      )}
       {/* 현재 리스크 및 조언 */}
      {risksAndAdvice && (
        <div className="report-section">
          <h4>⚠️ 현재 잠재적 리스크 및 조언</h4>
          <p className="summary" dangerouslySetInnerHTML={renderTextWithExplanation(risksAndAdvice.summary)}></p>
          {risksAndAdvice.details && risksAndAdvice.details.length > 0 && (
            <ul className="details-list risk-list">
              {risksAndAdvice.details.map((item, index) => (
                <li key={index}>
                  <span className="item-label">{item.item}:</span>
                  {/* 상태 텍스트에 함수 적용 */}
                  <span className="item-status" dangerouslySetInnerHTML={renderTextWithExplanation(item.status)}></span>
                  <span className="item-advice">{item.advice}</span>
                  <span className="item-cost">(예상 비용: {item.estimatedCost})</span>
                </li>
              ))}
            </ul>
          )}
           {/* 가격 가이드 텍스트에 함수 적용 */}
          <p className="price-guidance"><strong dangerouslySetInnerHTML={renderTextWithExplanation("가격 가이드:")}></strong> <span dangerouslySetInnerHTML={renderTextWithExplanation(risksAndAdvice.priceGuidance || '정보 없음')}></span></p>
        </div>
      )}
      {/* AI 예측 시세 */}
      {predictedPrice && (
        <div className="report-section price-section">
          <h4>💰 AI 예측 적정 시세</h4>
          <p className="predicted-range">{predictedPrice.range || '정보 없음'}</p>
          <p className="prediction-basis"><strong dangerouslySetInnerHTML={renderTextWithExplanation("예측 근거:")}></strong> <span dangerouslySetInnerHTML={renderTextWithExplanation(predictedPrice.basis || '정보 없음')}></span></p>
        </div>
      )}
      {/* AI 유지보수 예측 */}
      {maintenancePrediction && (
        <div className="report-section maintenance-section">
          <h4>🛠️ AI 향후 유지보수 예측</h4>
          {maintenancePrediction.majorItems && maintenancePrediction.majorItems.length > 0 && (
            <>
              <p className="sub-heading">예상 주요 정비 항목:</p>
              <ul className="details-list maintenance-list">
                {maintenancePrediction.majorItems.map((item, index) => (
                  <li key={index}>
                    <span className="item-label" dangerouslySetInnerHTML={renderTextWithExplanation(item.item)}></span>
                    <span className="item-timing">시기: {item.timing}</span>
                    <span className="item-cost">(예상 비용: {item.estimatedCost})</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {maintenancePrediction.commonIssues && maintenancePrediction.commonIssues.length > 0 && (
            <>
              <p className="sub-heading">해당 차종 주의사항 (고질병):</p>
              <ul className="details-list issue-list">
                {maintenancePrediction.commonIssues.map((issue, index) => (
                  <li key={index} dangerouslySetInnerHTML={renderTextWithExplanation(issue)}></li>
                ))}
              </ul>
            </>
          )}
          {maintenancePrediction.overallAdvice && (
             <p className="overall-advice"><strong dangerouslySetInnerHTML={renderTextWithExplanation("종합 조언:")}></strong> <span dangerouslySetInnerHTML={renderTextWithExplanation(maintenancePrediction.overallAdvice)}></span></p>
          )}
        </div>
      )}

      {/* 모달 컴포넌트 */}
      <TermModal
        isOpen={modalOpen}
        term={modalTerm}
        explanation={modalExplanation}
        isLoading={modalLoading}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}

export default AnalysisReport;