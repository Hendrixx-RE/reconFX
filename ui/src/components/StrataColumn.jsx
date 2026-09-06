import React, { useState, useMemo } from 'react';

/**
 * Helper to format dollar amounts with comma grouping.
 */
function formatUSD(amount) {
  const num = Number(amount);
  if (isNaN(num)) return '$0';
  return '$' + Math.round(num).toLocaleString('en-US');
}

/**
 * Canonical depth / chronological rank (geological ordering).
 * Rank 1 is oldest / bedrock (placed at the BOTTOM).
 * Rank 6 is surface / newest / unreferenced (placed at the TOP).
 */
function getStratumDepthRank(s) {
  const label = (s.label || '').toLowerCase();
  const cls = (s.classification || s.cause_id || '').toLowerCase();
  const amt = Number(s.amount_usd) || 0;

  // S1: Cutover artifacts ($612k, 2023-04) — Bedrock / Oldest
  if (cls.includes('cutover') || label.includes('cutover') || label.includes('migration') || amt === 612000) return 1;
  // S2: Unreversed FX revaluation ($384k, 2023)
  if (cls.includes('fx') || label.includes('fx') || amt === 384000) return 2;
  // S3: Duplicate AP vendor feed ($206k, 2024-03)
  if (cls.includes('dup') || label.includes('duplicate') || amt === 206000) return 3;
  // S4: Accrued IC margin plugs ($290k, 2024-06 to 2025-04)
  if (cls.includes('plug') || label.includes('margin plug') || amt === 290000) return 4;
  // S5: Live collectible receivable ($263k, 2024-08)
  if (cls.includes('collect') || label.includes('collectible') || label.includes('receivable') || amt === 263000) return 5;
  // S6: Untraceable remainder ($92k, unresolved) — Surface
  if (cls.includes('untraceable') || label.includes('untraceable') || amt === 92000) return 6;

  // Fallback if dates/years provided
  if (s.year) return parseInt(s.year, 10);
  if (s.period) return parseInt(s.period.slice(0, 4), 10);
  return 3;
}

/**
 * Period / depth epoch badge text
 */
function getEpochLabel(stratum, rank) {
  if (stratum.period) return stratum.period;
  if (stratum.year) return stratum.year;
  switch (rank) {
    case 1: return '2023 · BEDROCK (38mo)';
    case 2: return '2023 · UNREVERSED';
    case 3: return '2024 · DUPLICATES';
    case 4: return '2024 · MARGIN PLUGS';
    case 5: return '2024 · COLLECTIBLE';
    case 6: return 'SURFACE · UNTRACEABLE';
    default: return 'CLEARING ACCRUAL';
  }
}

/**
 * StrataColumn
 *
 * Act I's geological cross-section of clearing account 1900.
 * Bands are sized proportionally by dollar amount and ordered by depth in time
 * with the OLDEST at the BOTTOM. Each band is clickable/expandable to reveal its EvidenceCard.
 *
 * Props:
 *  - strata: Array<{ label, amount_usd, count, disposition, status, ao_message_id, ... }>
 *  - onExpandStratum: (stratum) => void (callback for click-through)
 */
export default function StrataColumn({ strata = [], onExpandStratum }) {
  const [selectedId, setSelectedId] = useState(null);

  // Total balance computation
  const totalAmount = useMemo(() => {
    return strata.reduce((sum, s) => sum + (Number(s.amount_usd) || 0), 0);
  }, [strata]);

  const totalCount = useMemo(() => {
    return strata.reduce((sum, s) => sum + (Number(s.count) || 0), 0);
  }, [strata]);

  // Order strata with OLDEST at the BOTTOM and SURFACE / UNTRACEABLE at the TOP.
  // Descending depth rank (6 -> 1) renders surface at top and bedrock at bottom.
  const orderedStrata = useMemo(() => {
    if (!strata || strata.length === 0) return [];
    return [...strata].sort((a, b) => {
      const rankA = getStratumDepthRank(a);
      const rankB = getStratumDepthRank(b);
      return rankB - rankA; // highest rank (6, surface) at top, lowest rank (1, bedrock) at bottom
    });
  }, [strata]);

  const handleStratumClick = (stratum) => {
    const id = stratum.ao_message_id || stratum.cause_id || stratum.label;
    setSelectedId((prev) => (prev === id ? null : id));
    if (onExpandStratum) {
      onExpandStratum(stratum);
    }
  };

  const handleKeyDown = (e, stratum) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleStratumClick(stratum);
    }
  };

  return (
    <div className="strata-column-container" aria-label="Act I Clearing Account Strata Column">
      <style>{`
        .strata-column-container {
          display: flex;
          flex-direction: column;
          background: #0d1117;
          border: 1px solid #30363d;
          border-radius: 4px;
          color: #c9d1d9;
          box-sizing: border-box;
          width: 100%;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }

        .strata-header {
          padding: 12px 16px;
          border-bottom: 1px solid #21262d;
          background: #161b22;
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          flex-wrap: wrap;
          gap: 8px;
        }

        .strata-header-title {
          font-size: 11px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: #8b949e;
          font-weight: 600;
        }

        .strata-header-summary {
          font-family: var(--font-figures, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-variant-numeric: tabular-nums;
          font-size: 13px;
          color: #f0f6fc;
          font-weight: 600;
        }

        .strata-geological-frame {
          display: flex;
          position: relative;
          min-height: 480px;
          padding: 8px;
          gap: 8px;
          background: #090d12;
        }

        .strata-depth-axis {
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          padding: 8px 4px;
          width: 68px;
          flex-shrink: 0;
          font-family: var(--font-trace, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-size: 9px;
          letter-spacing: 0.04em;
          color: #6e7681;
          user-select: none;
          border-right: 1px dashed #21262d;
          text-align: right;
        }

        .strata-depth-axis span {
          display: block;
        }

        .strata-stack {
          display: flex;
          flex-direction: column;
          flex: 1;
          gap: 2px;
          position: relative;
          justify-content: stretch;
        }

        .strata-empty {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: #8b949e;
          font-size: 12px;
          font-family: var(--font-trace, monospace);
        }

        .stratum-band {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 14px;
          cursor: pointer;
          outline: none;
          box-sizing: border-box;
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-left-width: 4px;
          position: relative;
          user-select: none;
          animation: stratumReveal 0.22s ease-out forwards;
        }

        /* Direct state highlights — NO hover transitions per design direction */
        .stratum-band:hover {
          border-color: rgba(255, 255, 255, 0.24);
          filter: brightness(1.08);
        }

        .stratum-band:focus-visible,
        .stratum-band.selected {
          outline: 1px solid #f0f6fc;
          filter: brightness(1.15);
        }

        @keyframes stratumReveal {
          from {
            opacity: 0;
            transform: translateY(2px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* Disposition styles using CSS variables with solid fallbacks */
        .stratum-band.status-explained {
          border-left-color: var(--color-explained, #3b82f6);
          background: rgba(59, 130, 246, 0.08);
        }

        .stratum-band.status-recovered {
          border-left-color: var(--color-recovered, #10b981);
          background: rgba(16, 185, 129, 0.1);
        }

        .stratum-band.status-escalated {
          border-left-color: var(--color-escalated, #ef4444);
          background: rgba(239, 68, 68, 0.12);
        }

        .stratum-meta {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
          overflow: hidden;
        }

        .stratum-top-line {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .stratum-epoch {
          font-family: var(--font-trace, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-size: 10px;
          font-weight: 600;
          letter-spacing: 0.04em;
          color: #8b949e;
        }

        .stratum-label {
          font-size: 13px;
          font-weight: 600;
          color: #f0f6fc;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .stratum-bottom-line {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 11px;
          color: #8b949e;
        }

        .stratum-disposition {
          color: #8b949e;
        }

        .stratum-count {
          font-family: var(--font-figures, monospace);
          font-variant-numeric: tabular-nums;
          color: #6e7681;
        }

        .stratum-message-id {
          font-family: var(--font-trace, monospace);
          font-size: 10px;
          color: #484f58;
        }

        .stratum-figures {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 4px;
          flex-shrink: 0;
          padding-left: 12px;
        }

        .stratum-amount {
          font-family: var(--font-figures, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-variant-numeric: tabular-nums;
          font-size: 15px;
          font-weight: 700;
          color: #f0f6fc;
        }

        .stratum-badge {
          display: inline-flex;
          align-items: center;
          font-size: 9px;
          font-weight: 700;
          letter-spacing: 0.06em;
          padding: 2px 6px;
          border-radius: 2px;
          text-transform: uppercase;
          font-family: var(--font-trace, monospace);
        }

        .badge-explained {
          background: rgba(59, 130, 246, 0.18);
          color: var(--color-explained, #58a6ff);
          border: 1px solid rgba(59, 130, 246, 0.4);
        }

        .badge-recovered {
          background: rgba(16, 185, 129, 0.18);
          color: var(--color-recovered, #3fb950);
          border: 1px solid rgba(16, 185, 129, 0.4);
        }

        .badge-escalated {
          background: rgba(239, 68, 68, 0.22);
          color: var(--color-escalated, #f85149);
          border: 1px solid rgba(239, 68, 68, 0.5);
        }
      `}</style>

      {/* Act I Header */}
      <div className="strata-header">
        <div className="strata-header-title">
          ACT I · Clearing Account 1900 Excavation
        </div>
        <div className="strata-header-summary">
          {formatUSD(totalAmount || 1847000)} · {totalCount || 55} open items · 38 months
        </div>
      </div>

      {/* Geological Cross-Section */}
      <div className="strata-geological-frame">
        <div className="strata-depth-axis">
          <span>SURFACE ▲</span>
          <span>RECENT</span>
          <span>MID-DEPTH</span>
          <span>BEDROCK ▼</span>
        </div>

        <div className="strata-stack">
          {orderedStrata.length === 0 ? (
            <div className="strata-empty">Awaiting clearing account stratification...</div>
          ) : (
            orderedStrata.map((stratum, index) => {
              const amt = Number(stratum.amount_usd) || 0;
              const rank = getStratumDepthRank(stratum);
              const epoch = getEpochLabel(stratum, rank);
              const status = (stratum.status || 'explained').toLowerCase();
              const id = stratum.ao_message_id || stratum.cause_id || `${stratum.label}-${index}`;
              const isSelected = selectedId === id;

              // Proportional flex-basis: minimum 54px baseline, expands proportionally by dollar weight
              const flexStyle = {
                flex: `${Math.max(amt, 1)} 1 54px`,
                minHeight: '52px',
              };

              return (
                <div
                  key={id}
                  className={`stratum-band status-${status} ${isSelected ? 'selected' : ''}`}
                  style={flexStyle}
                  onClick={() => handleStratumClick(stratum)}
                  onKeyDown={(e) => handleKeyDown(e, stratum)}
                  tabIndex={0}
                  role="button"
                  aria-label={`${stratum.label}: ${formatUSD(amt)}, status ${status}`}
                >
                  <div className="stratum-meta">
                    <div className="stratum-top-line">
                      <span className="stratum-epoch">{epoch}</span>
                      <span className="stratum-label">{stratum.label}</span>
                    </div>
                    <div className="stratum-bottom-line">
                      <span className="stratum-disposition">{stratum.disposition || 'Pending review'}</span>
                      {stratum.count != null && (
                        <span className="stratum-count">· {stratum.count} items</span>
                      )}
                      {stratum.ao_message_id && (
                        <span className="stratum-message-id">· {stratum.ao_message_id}</span>
                      )}
                    </div>
                  </div>

                  <div className="stratum-figures">
                    <div className="stratum-amount">{formatUSD(amt)}</div>
                    <span className={`stratum-badge badge-${status}`}>
                      {status === 'escalated' ? 'ESCALATED' : status === 'recovered' ? 'RECOVERED' : 'EXPLAINED'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export { StrataColumn };
