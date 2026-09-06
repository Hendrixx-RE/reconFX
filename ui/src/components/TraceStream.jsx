import React, { useEffect, useRef } from 'react';

/**
 * Format currency with aligned decimals and tabular figures.
 */
function formatUSD(val) {
  if (val === null || val === undefined || val === '') return null;
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
 * Format timestamp into HH:MM:SS format.
 */
function formatTime(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return String(isoString);
    return d.toISOString().substring(11, 19);
  } catch {
    return String(isoString);
  }
}

/**
 * Clean badge styling helper.
 */
const badgeStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '1px 6px',
  borderRadius: '3px',
  fontSize: '11px',
  fontWeight: 600,
  lineHeight: '16px',
  letterSpacing: '0.02em',
};

/**
 * Render individual event row in the trace stream.
 */
function TraceEventItem({ event }) {
  const { event_type, act, timestamp, step, payload = {} } = event;
  const evidenceRefs = payload.evidence_refs || payload.supporting_evidence || [];
  const aoMessageId = payload.ao_message_id || event.ao_message_id;

  // Render specific content depending on event_type
  let typeBadge = null;
  let eventBody = null;

  switch (event_type) {
    case 'TOOL_CALL': {
      const toolName = payload.tool_name || payload.tool || payload.name || 'tool_call';
      const kwargs = payload.kwargs || payload.args;
      const result = payload.result;
      const isRetry = payload.retry;

      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: '#21262d',
            color: '#8b949e',
            border: '1px solid #30363d',
          }}
        >
          Tool call
        </span>
      );

      eventBody = (
        <div style={{ marginTop: '2px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, color: '#e6edf3' }}>{toolName}()</span>
            {isRetry && (
              <span style={{ color: '#d29922', fontSize: '11px' }}>
                (retry: {payload.error || 'malformed input'})
              </span>
            )}
          </div>

          {kwargs && Object.keys(kwargs).length > 0 && (
            <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '2px' }}>
              {Object.entries(kwargs).map(([k, v], i) => (
                <span key={k} style={{ marginRight: '8px' }}>
                  <span style={{ color: '#7d8590' }}>{k}:</span>{' '}
                  <span style={{ color: '#c9d1d9' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                  {i < Object.keys(kwargs).length - 1 ? ' · ' : ''}
                </span>
              ))}
            </div>
          )}

          {result && (
            <div style={{ fontSize: '12px', color: '#7d8590', marginTop: '3px' }}>
              {result.items ? (
                <span>→ {result.items.length} records retrieved</span>
              ) : result.summary ? (
                <span>→ {result.summary}</span>
              ) : typeof result === 'string' ? (
                <span>→ {result}</span>
              ) : null}
            </div>
          )}
        </div>
      );
      break;
    }

    case 'HYPOTHESIS': {
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: '#1f2937',
            color: '#93c5fd',
            border: '1px solid #374151',
          }}
        >
          Hypothesis
        </span>
      );

      const message = payload.message || payload.label || payload.hypothesis || payload.reason;
      const baseline = payload.baseline;
      const order = payload.cause_profile_order || payload.recommended_hypothesis_order;

      eventBody = (
        <div style={{ marginTop: '2px' }}>
          {message && (
            <div style={{ color: '#e6edf3', fontSize: '13px', lineHeight: '1.4' }}>
              {message}
            </div>
          )}
          {baseline && (
            <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>
              Opening deviation:{' '}
              <span style={{ fontFamily: 'var(--font-figures, monospace)', fontVariantNumeric: 'tabular-nums', color: '#f3f4f6' }}>
                {formatUSD(baseline.deviation)}
              </span>
              {' · '}
              Eligible base:{' '}
              <span style={{ fontFamily: 'var(--font-figures, monospace)', fontVariantNumeric: 'tabular-nums', color: '#f3f4f6' }}>
                {formatUSD(baseline.eligible_base)}
              </span>
            </div>
          )}
          {order && Array.isArray(order) && (
            <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>
              Prior order: {order.join(' → ')}
            </div>
          )}
        </div>
      );
      break;
    }

    case 'FACTOR_ACCEPTED': {
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: 'rgba(22, 163, 74, 0.15)',
            color: 'var(--color-explained, #16a34a)',
            border: '1px solid var(--color-explained, #16a34a)',
          }}
        >
          ✓ Accepted
        </span>
      );

      const causeId = payload.cause_id || '';
      const label = payload.label || '';
      const classification = payload.classification || '';
      const factorUsd = payload.factor_usd;
      const newResidual = payload.new_residual || payload.residual_after;
      const disposition = payload.disposition;

      eventBody = (
        <div style={{ marginTop: '2px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, color: '#f3f4f6' }}>
              {causeId ? `${causeId} · ` : ''}{label}
            </span>
            {factorUsd && (
              <span
                style={{
                  fontFamily: 'var(--font-figures, monospace)',
                  fontVariantNumeric: 'tabular-nums',
                  fontWeight: 600,
                  color: 'var(--color-explained, #16a34a)',
                }}
              >
                +{formatUSD(factorUsd)}
              </span>
            )}
          </div>

          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '3px' }}>
            {classification && <span>Classification: <span style={{ color: '#c9d1d9' }}>{classification}</span></span>}
            {disposition && <span> · Disposition: <span style={{ color: '#c9d1d9' }}>{disposition}</span></span>}
            {newResidual && (
              <span>
                {' '}· Residual:{' '}
                <span style={{ fontFamily: 'var(--font-figures, monospace)', fontVariantNumeric: 'tabular-nums', color: '#e6edf3' }}>
                  {formatUSD(newResidual)}
                </span>
              </span>
            )}
          </div>

          {payload.precedence_note && (
            <div style={{ fontSize: '11px', color: '#7d8590', marginTop: '2px', fontStyle: 'italic' }}>
              Precedence override: {payload.precedence_note}
            </div>
          )}
        </div>
      );
      break;
    }

    case 'FACTOR_REJECTED': {
      // Struck-through / muted styling. Use standard neutral colors, NOT --color-escalated.
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: '#21262d',
            color: '#737373',
            border: '1px solid #30363d',
            textDecoration: 'line-through',
          }}
        >
          ✗ Rejected
        </span>
      );

      const causeId = payload.cause_id || '';
      const hypothesis = payload.hypothesis || payload.classification || payload.label || '';
      const impact = payload.factor_usd || payload.computed_impact_usd;
      const reason = payload.rejection_reason;
      const threshold = payload.threshold_usd;

      eventBody = (
        <div style={{ marginTop: '2px', opacity: 0.8 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ textDecoration: 'line-through', color: '#8b949e', fontWeight: 500 }}>
              {causeId ? `${causeId} · ` : ''}{hypothesis}
            </span>
            {impact && (
              <span
                style={{
                  fontFamily: 'var(--font-figures, monospace)',
                  fontVariantNumeric: 'tabular-nums',
                  textDecoration: 'line-through',
                  color: '#737373',
                }}
              >
                {formatUSD(impact)}
              </span>
            )}
          </div>

          <div style={{ fontSize: '12px', color: '#737373', marginTop: '3px' }}>
            {reason === 'BELOW_MATERIALITY' ? (
              <span>
                Rejected below materiality gate ({formatUSD(impact)} &lt; threshold {formatUSD(threshold || 500)}) · Residual unchanged
              </span>
            ) : reason === 'TRANSACTION_SET_OVERLAP' ? (
              <span>Rejected: non-overlap constraint violation (overlapping line items)</span>
            ) : (
              <span>Reason: {reason || 'Materiality or evidentiary criteria not met'}</span>
            )}
          </div>
        </div>
      );
      break;
    }

    case 'RECOVERY_FOUND': {
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: 'rgba(2, 132, 199, 0.15)',
            color: 'var(--color-recovered, #0284c7)',
            border: '1px solid var(--color-recovered, #0284c7)',
          }}
        >
          + Recovery
        </span>
      );

      const label = payload.label || 'Recoverable entitlement';
      const entitlement = payload.entitlement_impact_usd || payload.factor_usd;
      const baseAmount = payload.amount_usd;

      eventBody = (
        <div style={{ marginTop: '2px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, color: '#f3f4f6' }}>{label}</span>
            {entitlement && (
              <span
                style={{
                  fontFamily: 'var(--font-figures, monospace)',
                  fontVariantNumeric: 'tabular-nums',
                  fontWeight: 600,
                  color: 'var(--color-recovered, #0284c7)',
                }}
              >
                +{formatUSD(entitlement)}
              </span>
            )}
          </div>

          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '3px' }}>
            {baseAmount && (
              <span>
                Base cost:{' '}
                <span style={{ fontFamily: 'var(--font-figures, monospace)', fontVariantNumeric: 'tabular-nums', color: '#c9d1d9' }}>
                  {formatUSD(baseAmount)}
                </span>
                {' · '}
              </span>
            )}
            <span>Separate axis (does not reduce closing residual)</span>
          </div>
        </div>
      );
      break;
    }

    case 'ESCALATION': {
      // The only place a high-alarm color appears
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: 'rgba(220, 38, 38, 0.15)',
            color: 'var(--color-escalated, #dc2626)',
            border: '1px solid var(--color-escalated, #dc2626)',
          }}
        >
          ! Escalation
        </span>
      );

      const residual = payload.residual_usd;
      const reason = payload.reason || 'RESIDUAL_UNEXPLAINED';
      const gap = payload.evidence_gap || [];

      eventBody = (
        <div style={{ marginTop: '2px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, color: 'var(--color-escalated, #dc2626)' }}>
              Execution halted · Controller sign-off required
            </span>
            {residual && (
              <span
                style={{
                  fontFamily: 'var(--font-figures, monospace)',
                  fontVariantNumeric: 'tabular-nums',
                  fontWeight: 700,
                  color: 'var(--color-escalated, #dc2626)',
                }}
              >
                Residual {formatUSD(residual)}
              </span>
            )}
          </div>

          <div style={{ fontSize: '12px', color: '#c9d1d9', marginTop: '3px' }}>
            Reason: {reason === 'RESIDUAL_UNEXPLAINED' ? 'Insufficient evidence to substantiate residual true-up' : reason}
          </div>

          {Array.isArray(gap) && gap.length > 0 && (
            <div style={{ marginTop: '6px', fontSize: '12px', color: '#8b949e' }}>
              <div style={{ color: '#f87171', fontWeight: 500, marginBottom: '2px' }}>
                Missing evidence required:
              </div>
              <ul style={{ margin: 0, paddingLeft: '16px', lineHeight: '1.4' }}>
                {gap.map((item, idx) => (
                  <li key={idx} style={{ color: '#e5e7eb' }}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
      break;
    }

    case 'DISPOSITION': {
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: '#21262d',
            color: '#d1d5db',
            border: '1px solid #30363d',
          }}
        >
          Disposition
        </span>
      );

      const causeId = payload.cause_id;
      const disp = payload.disposition;
      const treatment = payload.treatment;
      const authority = payload.authority;

      eventBody = (
        <div style={{ marginTop: '2px', fontSize: '12px', color: '#c9d1d9' }}>
          <span style={{ fontWeight: 600, color: '#f3f4f6' }}>{causeId ? `${causeId}: ` : ''}{disp}</span>
          {treatment && <span> — {treatment}</span>}
          {authority && <span style={{ color: '#8b949e' }}> ({authority})</span>}
        </div>
      );
      break;
    }

    case 'DECISION': {
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: '#1e3a8a',
            color: '#bfdbfe',
            border: '1px solid #2563eb',
          }}
        >
          Decision
        </span>
      );

      const decisionType = payload.decision_type || 'DECISION_RECORDED';
      const actor = payload.actor || 'Corporate Controller';

      eventBody = (
        <div style={{ marginTop: '2px', fontSize: '12px', color: '#e5e7eb' }}>
          <span style={{ fontWeight: 600 }}>{decisionType}</span>
          {' · '}
          <span style={{ color: '#9ca3af' }}>Actor: {actor}</span>
        </div>
      );
      break;
    }

    case 'COST': {
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: '#21262d',
            color: '#9ca3af',
            border: '1px solid #374151',
          }}
        >
          Cost
        </span>
      );

      eventBody = (
        <div style={{ marginTop: '2px', fontSize: '12px', color: '#9ca3af' }}>
          Tensormux routing: Fast {payload.fast_calls || 0} calls · Strong {payload.strong_calls || 0} calls
          {payload.total_cost_usd !== undefined && (
            <span> · <span style={{ fontFamily: 'var(--font-figures, monospace)', fontVariantNumeric: 'tabular-nums' }}>{formatUSD(payload.total_cost_usd)}</span></span>
          )}
        </div>
      );
      break;
    }

    default: {
      typeBadge = (
        <span
          style={{
            ...badgeStyle,
            backgroundColor: '#21262d',
            color: '#8b949e',
            border: '1px solid #30363d',
          }}
        >
          {event_type || 'Event'}
        </span>
      );

      eventBody = (
        <div style={{ marginTop: '2px', fontSize: '12px', color: '#c9d1d9' }}>
          {typeof payload === 'string' ? payload : JSON.stringify(payload)}
        </div>
      );
      break;
    }
  }

  return (
    <div
      style={{
        padding: '10px 14px',
        borderBottom: '1px solid #21262d',
        fontSize: '13px',
        lineHeight: '1.45',
        color: '#c9d1d9',
      }}
    >
      {/* Top line: step indicator, event type badge, timestamp, act */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {step !== undefined && (
            <span
              style={{
                fontSize: '11px',
                color: '#6e7681',
                fontFamily: 'var(--font-figures, monospace)',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              #{step}
            </span>
          )}
          {typeBadge}
          {act && (
            <span style={{ fontSize: '11px', color: '#6e7681', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {act}
            </span>
          )}
        </div>

        {timestamp && (
          <span
            style={{
              fontSize: '11px',
              color: '#6e7681',
              fontFamily: 'var(--font-figures, monospace)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {formatTime(timestamp)}
          </span>
        )}
      </div>

      {/* Main event content */}
      {eventBody}

      {/* Evidence References */}
      {Array.isArray(evidenceRefs) && evidenceRefs.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '6px' }}>
          {evidenceRefs.map((ref, i) => (
            <span
              key={i}
              title={ref}
              style={{
                fontSize: '11px',
                padding: '1px 6px',
                borderRadius: '3px',
                backgroundColor: '#161b22',
                border: '1px solid #30363d',
                color: '#8b949e',
                fontFamily: 'var(--font-figures, monospace)',
                maxWidth: '100%',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              ref: {ref}
            </span>
          ))}
        </div>
      )}

      {/* AO Message ID Pill */}
      {aoMessageId && (
        <div style={{ marginTop: '5px' }}>
          <span
            title={`Agent Orchestrator message: ${aoMessageId}`}
            style={{
              fontSize: '10px',
              padding: '1px 5px',
              borderRadius: '3px',
              backgroundColor: '#1c1e24',
              border: '1px solid #2d333b',
              color: '#7d8590',
              fontFamily: 'var(--font-figures, monospace)',
            }}
          >
            AO: {aoMessageId}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * TraceStream component.
 * Append-only log with auto-scroll for events arriving via WebSocket.
 */
export default function TraceStream({ events = [] }) {
  const containerRef = useRef(null);
  const bottomRef = useRef(null);

  // Auto-scroll on new events
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [events?.length]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: '200px',
        backgroundColor: '#0d1117',
        border: '1px solid #21262d',
        borderRadius: '6px',
        overflow: 'hidden',
        fontFamily: 'var(--font-trace, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif)',
      }}
    >
      {/* Stream Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          borderBottom: '1px solid #21262d',
          backgroundColor: '#161b22',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#f0f6fc' }}>
            Agent Trace Stream
          </span>
          <span
            style={{
              fontSize: '11px',
              padding: '1px 6px',
              borderRadius: '10px',
              backgroundColor: '#21262d',
              color: '#8b949e',
              fontFamily: 'var(--font-figures, monospace)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {events.length} {events.length === 1 ? 'event' : 'events'}
          </span>
        </div>
        <span style={{ fontSize: '11px', color: '#6e7681' }}>
          Append-only audit trail
        </span>
      </div>

      {/* Stream Body */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          minHeight: 0,
        }}
      >
        {(!events || events.length === 0) ? (
          <div
            style={{
              padding: '32px 16px',
              textAlign: 'center',
              color: '#6e7681',
              fontSize: '13px',
            }}
          >
            Awaiting agent execution events...
          </div>
        ) : (
          events.map((event, index) => (
            <TraceEventItem key={event.step !== undefined ? `${event.step}-${index}` : index} event={event} />
          ))
        )}
        <div ref={bottomRef} style={{ height: '1px' }} />
      </div>
    </div>
  );
}

export { TraceStream };
