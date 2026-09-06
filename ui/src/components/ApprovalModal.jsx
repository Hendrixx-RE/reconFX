import React, { useEffect } from 'react';

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
 * ApprovalModal component.
 * Displays the escalation packet (Appendix C schema):
 *  - Draft true-up journal entry lines (prominent)
 *  - Explicit evidence-gap statement (prominent)
 *  - Evidence chain (accepted factors, rejected hypotheses, recovery findings)
 *  - Plain active-voice Approve ("Approve true-up") and Reject actions
 */
export default function ApprovalModal({
  escalationPacket,
  isOpen = false,
  onApprove,
  onReject,
}) {
  // Listen for Escape key to dismiss
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onReject) {
        onReject();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onReject]);

  if (!isOpen) {
    return null;
  }

  const packet = escalationPacket?.packet || escalationPacket || {};
  const {
    escalation_id,
    entity_id = 'ENT-IN-02',
    period = '2026-03',
    opening_deviation_usd = 44000.0,
    explained_usd = 39000.0,
    residual_usd = 5000.0,
    factors = [],
    rejected_hypotheses = [],
    recovery_findings = [],
    probable_cause,
    confidence = 'PROBABLE_UNPROVEN',
    evidence_gap = [],
    proposed_journal_entry = {},
    ao_ledger_reference,
    neatlogs_trace_url,
  } = packet;

  const jeLines = proposed_journal_entry.lines || [];

  // Calculate journal entry totals
  const totalDebit = jeLines.reduce(
    (acc, l) => acc + (parseFloat(l.debit) || 0),
    0
  );
  const totalCredit = jeLines.reduce(
    (acc, l) => acc + (parseFloat(l.credit) || 0),
    0
  );
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.001 && totalDebit > 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="approval-modal-title"
      onClick={onReject}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(2px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        overflowY: 'auto',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '820px',
          maxHeight: '90vh',
          backgroundColor: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          fontFamily: 'var(--font-trace, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif)',
          color: '#c9d1d9',
          boxShadow: '0 24px 48px rgba(0, 0, 0, 0.6)',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: '#161b22',
            borderBottom: '1px solid #21262d',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span
                style={{
                  display: 'inline-block',
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-escalated, #dc2626)',
                }}
              />
              <h2
                id="approval-modal-title"
                style={{
                  margin: 0,
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#f0f6fc',
                }}
              >
                Escalation Review · Controller Sign-off Required
              </h2>
            </div>
            <div style={{ fontSize: '12px', color: '#8b949e' }}>
              <span>{entity_id}</span> · <span>{period} close</span>
              {escalation_id && <span> · Reference: {escalation_id}</span>}
            </div>
          </div>

          <button
            type="button"
            onClick={onReject}
            aria-label="Close dialog"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#8b949e',
              cursor: 'pointer',
              fontSize: '18px',
              lineHeight: 1,
              padding: '4px 8px',
              borderRadius: '3px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div
          style={{
            padding: '20px',
            overflowY: 'auto',
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
          }}
        >
          {/* Summary Figures Bar */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '12px',
              backgroundColor: '#161b22',
              border: '1px solid #21262d',
              borderRadius: '4px',
              padding: '12px 16px',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginBottom: '4px' }}>
                Opening deviation
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-figures, monospace)',
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#e6edf3',
                }}
              >
                {formatUSD(opening_deviation_usd)}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginBottom: '4px' }}>
                Forensically explained
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-figures, monospace)',
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: '16px',
                  fontWeight: 600,
                  color: 'var(--color-explained, #16a34a)',
                }}
              >
                {formatUSD(explained_usd)}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginBottom: '4px' }}>
                Unexplained residual
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-figures, monospace)',
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: '16px',
                  fontWeight: 700,
                  color: 'var(--color-escalated, #dc2626)',
                }}
              >
                {formatUSD(residual_usd)}
              </div>
            </div>
          </div>

          {/* Probable Cause & Confidence */}
          {probable_cause && (
            <div
              style={{
                fontSize: '12px',
                lineHeight: '1.5',
                color: '#c9d1d9',
                backgroundColor: '#161b22',
                border: '1px solid #21262d',
                borderRadius: '4px',
                padding: '10px 14px',
              }}
            >
              <div style={{ fontWeight: 600, color: '#f0f6fc', marginBottom: '2px' }}>
                Probable cause:
              </div>
              <div>{probable_cause}</div>
              {confidence && (
                <div style={{ marginTop: '4px', color: '#8b949e', fontSize: '11px' }}>
                  Confidence assessment:{' '}
                  <span style={{ color: '#e6edf3', fontWeight: 500 }}>{confidence}</span>
                  {' — billing-engine configuration export is required to confirm.'}
                </div>
              )}
            </div>
          )}

          {/* PROMINENT SECTION 1: Explicit Evidence Gap Statement */}
          <section
            style={{
              backgroundColor: 'rgba(220, 38, 38, 0.05)',
              border: '1px solid var(--color-escalated, #dc2626)',
              borderRadius: '4px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ color: 'var(--color-escalated, #dc2626)', fontWeight: 700, fontSize: '14px' }}>
                !
              </span>
              <h3
                style={{
                  margin: 0,
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#f0f6fc',
                }}
              >
                Evidence gap — required to substantiate residual
              </h3>
            </div>

            <p style={{ margin: '0 0 10px 0', fontSize: '12px', color: '#c9d1d9', lineHeight: '1.5' }}>
              The transfer-pricing engine has halted because an intercompany true-up without
              transaction-level substantiation risks disallowance and double taxation under OECD Pillar Two scrutiny.
              The following source documents are missing and must be obtained to substantiate the remaining{' '}
              <strong
                style={{
                  fontFamily: 'var(--font-figures, monospace)',
                  fontVariantNumeric: 'tabular-nums',
                  color: 'var(--color-escalated, #dc2626)',
                }}
              >
                {formatUSD(residual_usd)}
              </strong>{' '}
              adjustment:
            </p>

            {evidence_gap && evidence_gap.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {evidence_gap.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'baseline',
                      gap: '8px',
                      padding: '8px 10px',
                      backgroundColor: '#161b22',
                      border: '1px solid #30363d',
                      borderRadius: '3px',
                      fontSize: '12px',
                    }}
                  >
                    <span style={{ color: 'var(--color-escalated, #dc2626)', fontWeight: 600 }}>
                      Missing:
                    </span>
                    <span style={{ color: '#f0f6fc', flex: 1 }}>{item}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '12px', color: '#8b949e', fontStyle: 'italic' }}>
                No explicit evidence gap documented.
              </div>
            )}
          </section>

          {/* PROMINENT SECTION 2: Draft True-Up Journal Entry */}
          <section
            style={{
              backgroundColor: '#161b22',
              border: '1px solid #30363d',
              borderRadius: '4px',
              padding: '16px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'baseline',
                justifyContent: 'space-between',
                marginBottom: '10px',
              }}
            >
              <div>
                <h3
                  style={{
                    margin: 0,
                    fontSize: '14px',
                    fontWeight: 600,
                    color: '#f0f6fc',
                  }}
                >
                  Proposed journal entry · Draft true-up
                </h3>
                <span style={{ fontSize: '11px', color: '#8b949e' }}>
                  Status: DRAFT · Requires human controller sign-off
                </span>
              </div>

              {isBalanced && (
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: 'var(--color-explained, #16a34a)',
                    backgroundColor: 'rgba(22, 163, 74, 0.1)',
                    border: '1px solid var(--color-explained, #16a34a)',
                    padding: '2px 8px',
                    borderRadius: '3px',
                  }}
                >
                  Balanced entry ✓
                </span>
              )}
            </div>

            {jeLines.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '12px',
                    textAlign: 'left',
                  }}
                >
                  <thead>
                    <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                      <th style={{ padding: '6px 8px', fontWeight: 500 }}>Entity</th>
                      <th style={{ padding: '6px 8px', fontWeight: 500 }}>Account</th>
                      <th style={{ padding: '6px 8px', fontWeight: 500 }}>Description</th>
                      <th style={{ padding: '6px 8px', fontWeight: 500, textAlign: 'right' }}>
                        Debit (USD)
                      </th>
                      <th style={{ padding: '6px 8px', fontWeight: 500, textAlign: 'right' }}>
                        Credit (USD)
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {jeLines.map((line, idx) => (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: '1px solid #21262d',
                          backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.02)',
                        }}
                      >
                        <td style={{ padding: '8px', color: '#c9d1d9' }}>
                          {line.entity || entity_id || '—'}
                        </td>
                        <td style={{ padding: '8px' }}>
                          <code
                            style={{
                              fontFamily: 'var(--font-figures, monospace)',
                              color: '#f0f6fc',
                            }}
                          >
                            {line.account}
                          </code>
                        </td>
                        <td style={{ padding: '8px', color: '#e6edf3' }}>
                          {line.description}
                        </td>
                        <td
                          style={{
                            padding: '8px',
                            textAlign: 'right',
                            fontFamily: 'var(--font-figures, monospace)',
                            fontVariantNumeric: 'tabular-nums',
                            color: line.debit ? '#f0f6fc' : '#6e7681',
                          }}
                        >
                          {line.debit ? formatUSD(line.debit) : '—'}
                        </td>
                        <td
                          style={{
                            padding: '8px',
                            textAlign: 'right',
                            fontFamily: 'var(--font-figures, monospace)',
                            fontVariantNumeric: 'tabular-nums',
                            color: line.credit ? '#f0f6fc' : '#6e7681',
                          }}
                        >
                          {line.credit ? formatUSD(line.credit) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr
                      style={{
                        borderTop: '2px solid #30363d',
                        fontWeight: 600,
                        color: '#f0f6fc',
                      }}
                    >
                      <td colSpan={3} style={{ padding: '8px' }}>
                        Total
                      </td>
                      <td
                        style={{
                          padding: '8px',
                          textAlign: 'right',
                          fontFamily: 'var(--font-figures, monospace)',
                          fontVariantNumeric: 'tabular-nums',
                        }}
                      >
                        {formatUSD(totalDebit)}
                      </td>
                      <td
                        style={{
                          padding: '8px',
                          textAlign: 'right',
                          fontFamily: 'var(--font-figures, monospace)',
                          fontVariantNumeric: 'tabular-nums',
                        }}
                      >
                        {formatUSD(totalCredit)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <div style={{ fontSize: '12px', color: '#8b949e', fontStyle: 'italic' }}>
                No journal entry lines available.
              </div>
            )}
          </section>

          {/* Evidence Chain Section */}
          <section
            style={{
              backgroundColor: '#161b22',
              border: '1px solid #21262d',
              borderRadius: '4px',
              padding: '16px',
            }}
          >
            <h3
              style={{
                margin: '0 0 10px 0',
                fontSize: '13px',
                fontWeight: 600,
                color: '#f0f6fc',
              }}
            >
              Evidence chain · Prior substantiated factors
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
              {/* Accepted Factors */}
              {factors && factors.length > 0 ? (
                factors.map((f, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'baseline',
                      justifyContent: 'space-between',
                      padding: '6px 10px',
                      backgroundColor: '#0d1117',
                      border: '1px solid #21262d',
                      borderRadius: '3px',
                      gap: '8px',
                    }}
                  >
                    <div>
                      <span style={{ color: 'var(--color-explained, #16a34a)', fontWeight: 600, marginRight: '6px' }}>
                        ✓
                      </span>
                      <span style={{ color: '#e6edf3', fontWeight: 500 }}>
                        {f.cause_id ? `${f.cause_id} · ` : ''}{f.label || f.classification}
                      </span>
                      {f.evidence_refs && f.evidence_refs.length > 0 && (
                        <span style={{ color: '#8b949e', marginLeft: '6px', fontSize: '11px' }}>
                          (evidence: {f.evidence_refs.join(', ')})
                        </span>
                      )}
                    </div>
                    <span
                      style={{
                        fontFamily: 'var(--font-figures, monospace)',
                        fontVariantNumeric: 'tabular-nums',
                        color: 'var(--color-explained, #16a34a)',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      +{formatUSD(f.factor_usd)}
                    </span>
                  </div>
                ))
              ) : (
                <div style={{ color: '#8b949e', fontStyle: 'italic' }}>
                  No accepted factors recorded yet.
                </div>
              )}

              {/* Rejected Hypotheses */}
              {rejected_hypotheses && rejected_hypotheses.length > 0 && (
                <div style={{ marginTop: '4px' }}>
                  {rejected_hypotheses.map((h, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'baseline',
                        justifyContent: 'space-between',
                        padding: '6px 10px',
                        backgroundColor: '#0d1117',
                        border: '1px solid #21262d',
                        borderRadius: '3px',
                        opacity: 0.7,
                      }}
                    >
                      <div>
                        <span style={{ color: '#737373', marginRight: '6px' }}>✗</span>
                        <span style={{ color: '#8b949e', textDecoration: 'line-through' }}>
                          {h.hypothesis || 'Hypothesis'}
                        </span>
                        <span style={{ color: '#6e7681', marginLeft: '6px', fontSize: '11px' }}>
                          ({h.rejection_reason === 'BELOW_MATERIALITY'
                            ? `below ${formatUSD(h.threshold_usd || 500)} materiality gate`
                            : h.rejection_reason || 'rejected'})
                        </span>
                      </div>
                      <span
                        style={{
                          fontFamily: 'var(--font-figures, monospace)',
                          fontVariantNumeric: 'tabular-nums',
                          color: '#737373',
                          textDecoration: 'line-through',
                        }}
                      >
                        {formatUSD(h.computed_impact_usd)}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Recovery Findings */}
              {recovery_findings && recovery_findings.length > 0 && (
                <div style={{ marginTop: '4px' }}>
                  {recovery_findings.map((r, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'baseline',
                        justifyContent: 'space-between',
                        padding: '6px 10px',
                        backgroundColor: '#0d1117',
                        border: '1px solid #21262d',
                        borderRadius: '3px',
                      }}
                    >
                      <div>
                        <span style={{ color: 'var(--color-recovered, #0284c7)', fontWeight: 600, marginRight: '6px' }}>
                          +
                        </span>
                        <span style={{ color: '#e6edf3', fontWeight: 500 }}>
                          {r.label || 'Recoverable entitlement'}
                        </span>
                        <span style={{ color: '#8b949e', marginLeft: '6px', fontSize: '11px' }}>
                          (separate axis · recoverable)
                        </span>
                      </div>
                      <span
                        style={{
                          fontFamily: 'var(--font-figures, monospace)',
                          fontVariantNumeric: 'tabular-nums',
                          color: 'var(--color-recovered, #0284c7)',
                          fontWeight: 600,
                        }}
                      >
                        +{formatUSD(r.entitlement_impact_usd)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* Audit & Trace References */}
          {(ao_ledger_reference || neatlogs_trace_url) && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '16px',
                fontSize: '11px',
                color: '#6e7681',
                paddingTop: '4px',
              }}
            >
              {ao_ledger_reference && (
                <div>
                  <span>AO ledger reference: </span>
                  <code style={{ fontFamily: 'var(--font-figures, monospace)', color: '#8b949e' }}>
                    {ao_ledger_reference}
                  </code>
                </div>
              )}
              {neatlogs_trace_url && (
                <div>
                  <span>Neatlogs trace: </span>
                  <a
                    href={neatlogs_trace_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#58a6ff', textDecoration: 'none' }}
                  >
                    View execution trace
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer / Action Buttons */}
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: '#161b22',
            borderTop: '1px solid #21262d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ fontSize: '12px', color: '#8b949e' }}>
            Decision commits to the Agent Orchestrator audit log.
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Reject button: plain, active voice */}
            <button
              type="button"
              onClick={onReject}
              style={{
                backgroundColor: 'transparent',
                border: '1px solid #30363d',
                borderRadius: '4px',
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: 500,
                color: '#c9d1d9',
                cursor: 'pointer',
              }}
            >
              Reject
            </button>

            {/* Action button: per README: "Approve true-up" */}
            <button
              type="button"
              onClick={onApprove}
              style={{
                backgroundColor: 'var(--color-explained, #16a34a)',
                border: '1px solid #15803d',
                borderRadius: '4px',
                padding: '8px 18px',
                fontSize: '13px',
                fontWeight: 600,
                color: '#ffffff',
                cursor: 'pointer',
              }}
            >
              Approve true-up
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export { ApprovalModal };
