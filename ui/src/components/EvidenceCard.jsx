import React from 'react';

/**
 * Format currency with aligned decimals and tabular figures.
 */
function formatUSD(val) {
  if (val === null || val === undefined || val === '') return '$0.00';
  const num = typeof val === 'number' ? val : parseFloat(String(val).replace(/[^0-9.-]+/g, ''));
  if (isNaN(num)) return String(val);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Human-readable classification labels.
 */
const CLASSIFICATION_LABELS = {
  TIMING_UNBILLED: 'Timing difference (unbilled)',
  APPROVED_EXCLUSION: 'Approved policy exclusion',
  MISCLASSIFICATION: 'GL misclassification (recoverable)',
  FX_REVALUATION: 'FX revaluation',
  GENUINE_TP_DEVIATION: 'Genuine transfer-pricing deviation',
  LEGACY_MIGRATION: 'Legacy ERP cutover artifact',
  DUPLICATE_FEED: 'Duplicate AP vendor feed',
  COLLECTIBLE_RECEIVABLE: 'Live customer receivable',
  UNTRACEABLE: 'Untraceable balance',
};

/**
 * Human-readable disposition descriptions.
 */
const DISPOSITION_LABELS = {
  ROLL_TO_APRIL_BILLING: 'Roll into April billing run',
  RESTATE_COMPLIANCE_BASE: 'Restate compliance base (statutory audit log)',
  DRAFT_REVERSING_JE: 'Draft reversing journal entry',
  REINSTATE_AND_COLLECT: 'Reinstate and collect via payment rail',
  ESCALATE: 'Escalate to corporate controller',
  WRITE_OFF: 'P&L write-off (requires sign-off)',
};

/**
 * EvidenceCard component.
 * Displays substantiated factor data, transaction IDs, source documents,
 * classification, disposition, and immutable AO message reference.
 */
export default function EvidenceCard({ factor, onClose }) {
  if (!factor) {
    return (
      <div
        style={{
          padding: '16px',
          border: '1px solid #21262d',
          borderRadius: '4px',
          backgroundColor: '#0d1117',
          color: '#6e7681',
          fontSize: '13px',
          fontFamily: 'var(--font-trace, sans-serif)',
          textAlign: 'center',
        }}
      >
        No factor selected
      </div>
    );
  }

  const {
    cause_id,
    label,
    classification = '',
    transaction_ids = [],
    evidence_refs = [],
    factor_usd,
    disposition = '',
    ao_message_id,
  } = factor;

  const isRecovery =
    classification === 'MISCLASSIFICATION' ||
    disposition.includes('COLLECT') ||
    classification === 'COLLECTIBLE_RECEIVABLE';

  const isEscalated =
    disposition === 'ESCALATE' ||
    classification === 'UNTRACEABLE' ||
    classification === 'GENUINE_TP_DEVIATION';

  // Choose accent color based on disposition role
  const accentColor = isEscalated
    ? 'var(--color-escalated, #dc2626)'
    : isRecovery
    ? 'var(--color-recovered, #0284c7)'
    : 'var(--color-explained, #16a34a)';

  const classificationText = CLASSIFICATION_LABELS[classification] || classification.replace(/_/g, ' ');
  const dispositionText = DISPOSITION_LABELS[disposition] || disposition.replace(/_/g, ' ');

  return (
    <article
      style={{
        backgroundColor: '#161b22',
        border: '1px solid #30363d',
        borderLeft: `3px solid ${accentColor}`,
        borderRadius: '4px',
        padding: '16px',
        fontFamily: 'var(--font-trace, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif)',
        color: '#c9d1d9',
        fontSize: '13px',
        lineHeight: '1.5',
      }}
    >
      {/* Header: Cause ID, Label & Tabular Amount */}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          borderBottom: '1px solid #21262d',
          paddingBottom: '12px',
          marginBottom: '14px',
          gap: '12px',
        }}
      >
        <div>
          {cause_id && (
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: '#8b949e',
                marginRight: '6px',
                fontFamily: 'var(--font-figures, monospace)',
              }}
            >
              {cause_id}
            </span>
          )}
          <h3
            style={{
              display: 'inline',
              margin: 0,
              fontSize: '14px',
              fontWeight: 600,
              color: '#f0f6fc',
            }}
          >
            {label || 'Causal factor'}
          </h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              fontFamily: 'var(--font-figures, monospace)',
              fontVariantNumeric: 'tabular-nums',
              fontSize: '16px',
              fontWeight: 600,
              color: accentColor,
              whiteSpace: 'nowrap',
            }}
          >
            {formatUSD(factor_usd)}
          </div>
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close evidence card"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#8b949e',
                cursor: 'pointer',
                fontSize: '14px',
                padding: '2px 4px',
                lineHeight: '1',
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Structured Details Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {/* Classification */}
        <div style={{ display: 'flex', alignItems: 'flex-start' }}>
          <span style={{ width: '130px', flexShrink: 0, color: '#8b949e', fontSize: '12px' }}>
            Classification
          </span>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ color: '#e6edf3', fontWeight: 500 }}>{classificationText}</span>
            {classification && (
              <code
                style={{
                  fontSize: '11px',
                  padding: '1px 5px',
                  borderRadius: '3px',
                  backgroundColor: '#0d1117',
                  border: '1px solid #21262d',
                  color: '#8b949e',
                  fontFamily: 'var(--font-figures, monospace)',
                }}
              >
                {classification}
              </code>
            )}
          </div>
        </div>

        {/* Disposition */}
        <div style={{ display: 'flex', alignItems: 'flex-start' }}>
          <span style={{ width: '130px', flexShrink: 0, color: '#8b949e', fontSize: '12px' }}>
            Disposition
          </span>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ color: '#e6edf3' }}>{dispositionText}</span>
            {disposition && (
              <code
                style={{
                  fontSize: '11px',
                  padding: '1px 5px',
                  borderRadius: '3px',
                  backgroundColor: '#0d1117',
                  border: '1px solid #21262d',
                  color: '#8b949e',
                  fontFamily: 'var(--font-figures, monospace)',
                }}
              >
                {disposition}
              </code>
            )}
          </div>
        </div>

        {/* Transaction IDs */}
        <div style={{ display: 'flex', alignItems: 'flex-start' }}>
          <span style={{ width: '130px', flexShrink: 0, color: '#8b949e', fontSize: '12px' }}>
            Transactions {transaction_ids.length > 0 ? `(${transaction_ids.length})` : ''}
          </span>
          <div style={{ flex: 1, display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {transaction_ids.length > 0 ? (
              transaction_ids.map((txId, idx) => (
                <code
                  key={idx}
                  style={{
                    fontSize: '11px',
                    padding: '2px 6px',
                    borderRadius: '3px',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    color: '#c9d1d9',
                    fontFamily: 'var(--font-figures, monospace)',
                  }}
                >
                  {txId}
                </code>
              ))
            ) : (
              <span style={{ color: '#6e7681', fontStyle: 'italic' }}>No transactions linked</span>
            )}
          </div>
        </div>

        {/* Source Documents (from evidence_refs) */}
        <div style={{ display: 'flex', alignItems: 'flex-start' }}>
          <span style={{ width: '130px', flexShrink: 0, color: '#8b949e', fontSize: '12px' }}>
            Source documents
          </span>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {evidence_refs.length > 0 ? (
              evidence_refs.map((ref, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <code
                    style={{
                      fontSize: '11px',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      backgroundColor: '#0d1117',
                      border: '1px solid #30363d',
                      color: '#8b949e',
                      fontFamily: 'var(--font-figures, monospace)',
                      wordBreak: 'break-all',
                    }}
                  >
                    {ref}
                  </code>
                </div>
              ))
            ) : (
              <span style={{ color: '#6e7681', fontStyle: 'italic' }}>No corroborating documents</span>
            )}
          </div>
        </div>

        {/* AO Message ID */}
        {ao_message_id && (
          <div style={{ display: 'flex', alignItems: 'flex-start', paddingTop: '4px' }}>
            <span style={{ width: '130px', flexShrink: 0, color: '#8b949e', fontSize: '12px' }}>
              AO message ID
            </span>
            <div style={{ flex: 1 }}>
              <code
                style={{
                  fontSize: '11px',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  backgroundColor: '#0d1117',
                  border: '1px solid #21262d',
                  color: '#7d8590',
                  fontFamily: 'var(--font-figures, monospace)',
                  wordBreak: 'break-all',
                }}
              >
                {ao_message_id}
              </code>
            </div>
          </div>
        )}
      </div>
    </article>
  );
}

export { EvidenceCard };
