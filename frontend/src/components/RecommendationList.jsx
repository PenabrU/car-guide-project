import React from 'react';
import './RecommendationList.css';

function RecommendationList({ recommendData }) {
  if (!recommendData || typeof recommendData !== 'object') {
     return <p className="no-results">추천 데이터를 표시할 수 없습니다.</p>;
  }

  if (recommendData.error) {
    return (
      <div className="error-box">
        <p style={{ color: 'red' }}><strong>오류:</strong> {recommendData.error}</p>
        <p><strong>Raw Response:</strong></p>
        <pre className="raw-text">{recommendData.raw_text || 'No raw text available.'}</pre>
      </div>
    );
  }

  const { recommendations } = recommendData;

  if (!recommendations || recommendations.length === 0) {
    return <p className="no-results">추천된 차량이 없습니다.</p>;
  }

  return (
    <div className="recommendation-list">
      {recommendations.map((car) => (
        <div key={car.rank} className="recommendation-item card">
          <div className="card-header">
            <span className="rank-badge">{car.rank}</span>
            <h4 className="model-name">{car.modelName}</h4>
          </div>
          <div className="card-body">
            <p className="reason"><span className="label">추천 이유:</span> {car.reason}</p>
            <p className="price"><span className="label">예상 시세:</span> {car.priceRange}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default RecommendationList;