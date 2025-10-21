// frontend/src/components/TermModal.jsx
import React from 'react';
import './TermModal.css';

function TermModal({ isOpen, term, explanation, isLoading, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}> {/* 이벤트 버블링 방지 */}
        <button className="modal-close-button" onClick={onClose}>×</button>
        <h3>"{term}" 용어 설명</h3>
        <div className="modal-body">
          {isLoading ? (
            <div className="modal-loading">
              <span className="loading-spinner-modal"></span> 설명 생성 중...
            </div>
          ) : (
            <p>{explanation}</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default TermModal;