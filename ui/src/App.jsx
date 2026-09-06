import React, { useState, useEffect } from 'react';

// Dynamic component loader for components built by parallel workers.
// If the worker component exists, it will be loaded; otherwise fallback stubs render.
const componentModules = import.meta.glob('./components/*.jsx', { eager: true });

// Canonical Data per Section 4 & 7 of README
const CANONICAL_STRATA = [
  {
    label: 'cutover',
    period: '2023',
    description: 'ERP cutover residue (migration log match)',
    amount_usd: 612000,
    count: 9,
    disposition: 'WRITE_OFF_ESCALATED',
    status: 'explained',
    ao_message_id: 'ao-msg-strata-001'
  },
  {
    label: 'FX unreversed',
    period: '2023',
    description: 'Unreversed FX revaluation',
    amount_usd: 384000,
    count: 6,
    disposition: 'DRAFT_REVERSING_JE',
    status: 'explained',
    ao_message_id: 'ao-msg-strata-002'
  },
  {
    label: 'duplicates',
    period: '2024',
    description: 'Duplicate AP vendor feed (14 entries, same ref)',
    amount_usd: 206000,
    count: 14,
    disposition: 'DRAFT_REVERSAL_FEED',
    status: 'explained',
    ao_message_id: 'ao-msg-strata-003'
  },
  {
    label: 'margin plugs',
    period: '2024',
    description: 'Accrued IC margin plugs across 11 months (seeds Act II)',
    amount_usd: 290000,
    count: 11,
    disposition: 'REOPEN_PROFILE_SEEDED',
    status: 'explained',
    highlighted: true,
    ao_message_id: 'ao-msg-strata-004'
  },
  {
    label: 'collectible',
    period: '2024',
    description: 'Live collectible receivable (CUST-4471)',
    amount_usd: 263000,
    count: 3,
    disposition: 'REINSTATE_DODO_COLLECT',
    status: 'recovered',
    ao_message_id: 'ao-msg-strata-005'
  },
  {
    label: 'untraceable',
    period: '————',
    description: 'Suspense residue lacking corroboration',
    amount_usd: 92000,
    count: 12,
    disposition: 'ESCALATE_EVIDENCE_GAP',
    status: 'escalated',
    ao_message_id: 'ao-msg-strata-006'
  }
];

const CANONICAL_FACTORS = [
  {
    cause_id: 'F1',
    label: 'timing',
    title: 'Unbilled late payroll',
    classification: 'TIMING_UNBILLED',
    factor_usd: 31000,
    residual_after: 13000,
    disposition: 'ROLL_TO_APRIL_BILLING',
    status: 'accepted',
    evidence_refs: ['payroll_register.csv#PAY-2026-M2', 'tp_policy.json#billing_cutoff_day_of_month'],
    transaction_ids: ['GL-2026-0307'],
    ao_message_id: 'ao-msg-factor-001'
  },
  {
    cause_id: 'F2',
    label: 'exclusion',
    title: 'Approved restructuring severance',
    classification: 'APPROVED_POLICY_EXCEPTION',
    factor_usd: 8000,
    residual_after: 5000,
    disposition: 'PERMANENT_EXCLUSION_UPHELD',
    status: 'accepted',
    evidence_refs: ['policy_exceptions.json#EXP-2026-08', 'intercompany_invoice_lines.csv#INV-IC-2026-03-L5'],
    transaction_ids: ['GL-2026-0306'],
    ao_message_id: 'ao-msg-factor-002'
  },
  {
    cause_id: 'H3',
    label: 'FX — rejected',
    title: 'FX revaluation below materiality',
    classification: 'FX_REVALUATION',
    factor_usd: 340,
    residual_after: 5000,
    disposition: 'BELOW_MATERIALITY_REJECTED',
    status: 'rejected',
    evidence_refs: ['entity_gl.csv#GL-2026-0309', 'tp_policy.json#materiality_threshold_usd'],
    transaction_ids: ['GL-2026-0309'],
    ao_message_id: 'ao-msg-factor-003'
  }
];

const CANONICAL_RECOVERY = [
  {
    id: 'REC-01',
    label: 'Misclassified rechargeable software',
    amount_usd: 140000,
    entitlement_impact_usd: 14000,
    proposed_entry: 'Dr 6100 / Cr 6800 $140,000',
    evidence_refs: ['entity_gl.csv#GL-2026-0305', 'tp_policy.json#eligible_gl_accounts']
  }
];

const CANONICAL_ESCALATION = {
  escalation_id: 'ESC-2026-03-001',
  entity_id: 'ENT-IN-02',
  period: '2026-03',
  opening_deviation_usd: 44000.0,
  explained_usd: 39000.0,
  residual_usd: 5000.0,
  factors: CANONICAL_FACTORS,
  rejected_hypotheses: [
    {
      hypothesis: 'FX_REVALUATION',
      computed_impact_usd: 340.0,
      rejection_reason: 'BELOW_MATERIALITY',
      threshold_usd: 500.0
    }
  ],
  recovery_findings: CANONICAL_RECOVERY,
  probable_cause: 'Effective markup 9.79% applied against contractual 10.00% on billed base $2,370,000',
  confidence: 'PROBABLE_UNPROVEN',
  evidence_gap: [
    'March 2026 billing-run configuration export (markup rate parameter)',
    'Billing engine change log for period 2026-03-01 to 2026-03-25'
  ],
  proposed_journal_entry: {
    type: 'TP_TRUE_UP',
    status: 'DRAFT',
    requires_approval: true,
    lines: [
      { entity: 'ENT-IN-02', account: '1200', description: 'Intercompany Receivable - US Parent', debit: 5000.0, credit: 0 },
      { entity: 'ENT-IN-02', account: '4100', description: 'Intercompany Service Revenue', debit: 0, credit: 5000.0 },
      { entity: 'ENT-US-01', account: '6300', description: 'Intercompany Engineering Expense', debit: 5000.0, credit: 0 },
      { entity: 'ENT-US-01', account: '2100', description: 'Intercompany Payable - India Sub', debit: 0, credit: 5000.0 }
    ]
  },
  ao_ledger_reference: '0x7b19a4e0c892f3a',
  neatlogs_trace_url: 'https://neatlogs.com/traces/tr-recon-20260331-01'
};

const CANONICAL_TRACE_EVENTS = [
  {
    event_type: 'TOOL_CALL',
    act: 'EXCAVATION',
    timestamp: '2026-03-31T10:14:02Z',
    step: 1,
    payload: { tool: 'query_clearing_account()', output: '55 open items, balance $1,847,000 across 38 months' }
  },
  {
    event_type: 'HYPOTHESIS',
    act: 'EXCAVATION',
    timestamp: '2026-03-31T10:14:05Z',
    step: 2,
    payload: { hypothesis: 'cutover residue', evidence: 'migration_log.json' }
  },
  {
    event_type: 'FACTOR_ACCEPTED',
    act: 'EXCAVATION',
    timestamp: '2026-03-31T10:14:09Z',
    step: 3,
    payload: { label: 'cutover', amount_usd: 612000, ao_message_id: 'ao-msg-strata-001' }
  },
  {
    event_type: 'BRIDGE',
    act: 'BRIDGE',
    timestamp: '2026-03-31T10:14:15Z',
    step: 4,
    payload: { message: 'Prior from 11 plug months: timing 0.64 → test first' }
  },
  {
    event_type: 'TOOL_CALL',
    act: 'INVESTIGATION',
    timestamp: '2026-03-31T10:14:18Z',
    step: 5,
    payload: { tool: 'query_payroll()', output: 'PAY-2026-M2 posted 03-28 (cutoff day 25)' }
  },
  {
    event_type: 'FACTOR_ACCEPTED',
    act: 'INVESTIGATION',
    timestamp: '2026-03-31T10:14:22Z',
    step: 6,
    payload: { label: 'timing', amount_usd: 31000, residual_after: 13000, ao_message_id: 'ao-msg-factor-001' }
  },
  {
    event_type: 'FACTOR_REJECTED',
    act: 'INVESTIGATION',
    timestamp: '2026-03-31T10:14:27Z',
    step: 7,
    payload: { label: 'FX revaluation', amount_usd: 340, reason: 'below $500 materiality' }
  },
  {
    event_type: 'ESCALATION',
    act: 'INVESTIGATION',
    timestamp: '2026-03-31T10:14:30Z',
    step: 8,
    payload: {
      residual_usd: 5000,
      evidence_gap: 'billing-run config export, March 2026',
      ao_message_id: 'ao-msg-esc-001'
    }
  }
];

export function formatUSD(val) {
  if (val === undefined || val === null || isNaN(val)) return '$0';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(val);
}

// -----------------------------------------------------------------------------
// Component Placeholders matching prop contracts
// -----------------------------------------------------------------------------

function PlaceholderTraceStream({ events = [] }) {
  const displayEvents = events.length > 0 ? events : CANONICAL_TRACE_EVENTS;

  return (
    <div className="placeholder-stub" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="placeholder-header">
        <span>Trace Stream ({displayEvents.length} events)</span>
        <span className="num-figure">append-only</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {displayEvents.map((evt, idx) => {
          if (evt.event_type === 'BRIDGE') {
            return <div key={idx} className="trace-bridge-divider" />;
          }

          const isTool = evt.event_type === 'TOOL_CALL';
          const isAccepted = evt.event_type === 'FACTOR_ACCEPTED';
          const isRejected = evt.event_type === 'FACTOR_REJECTED';
          const isEscalation = evt.event_type === 'ESCALATION';

          return (
            <div
              key={idx}
              className={`trace-log-item ${isTool ? 'tool' : ''} ${isAccepted ? 'decision' : ''} ${isEscalation ? 'escalation' : ''}`}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-muted)', fontSize: '11px' }}>
                <span>{evt.act || 'TRACE'} · step {evt.step ?? idx + 1}</span>
                <span className="num-figure">{evt.timestamp ? evt.timestamp.slice(11, 19) : ''}</span>
              </div>
              <div style={{ marginTop: '2px', fontWeight: isAccepted || isEscalation ? 600 : 400 }}>
                {isTool && evt.payload?.tool && <div>&gt; {evt.payload.tool}</div>}
                {isTool && evt.payload?.output && <div style={{ color: 'var(--color-text-muted)', paddingLeft: '12px' }}>{evt.payload.output}</div>}
                {isAccepted && <div>✓ accepted {formatUSD(evt.payload?.amount_usd || evt.payload?.factor_usd)} ({evt.payload?.label})</div>}
                {isRejected && <div style={{ color: 'var(--color-text-muted)', textDecoration: 'line-through' }}>✗ rejected {formatUSD(evt.payload?.amount_usd || evt.payload?.factor_usd)} ({evt.payload?.reason || evt.payload?.label})</div>}
                {isEscalation && (
                  <div style={{ color: 'var(--color-escalated)' }}>
                    ESCALATE residual {formatUSD(evt.payload?.residual_usd)}
                    {evt.payload?.evidence_gap && (
                      <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 400 }}>
                        gap: {evt.payload.evidence_gap}
                      </div>
                    )}
                  </div>
                )}
                {!isTool && !isAccepted && !isRejected && !isEscalation && (
                  <div>{evt.payload?.hypothesis ? `Hypothesis: ${evt.payload.hypothesis}` : JSON.stringify(evt.payload || evt)}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PlaceholderStrataColumn({ strata = [] }) {
  // Geological metaphor: oldest content sits lower (bottom)
  const displayStrata = strata.length > 0 ? strata : CANONICAL_STRATA;

  return (
    <div className="placeholder-stub" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="placeholder-header">
        <span>Act I Geological Section (bands sized by amount, oldest at bottom)</span>
        <span className="num-figure">Account 1900</span>
      </div>
      <div className="strata-placeholder-column">
        {displayStrata.map((s, idx) => (
          <div
            key={idx}
            className={`stratum-band ${s.highlighted ? 'highlighted' : ''} ${s.status === 'escalated' ? 'escalated' : ''}`}
            style={{
              minHeight: `${Math.max(28, Math.min(64, Math.round(s.amount_usd / 15000)))}px`
            }}
          >
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span className="num-figure" style={{ color: 'var(--color-text-muted)', width: '36px' }}>{s.period || '2024'}</span>
              <span style={{ fontWeight: 500 }}>{s.label}</span>
              {s.count && <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>({s.count} items)</span>}
              {s.highlighted && <span style={{ color: 'var(--color-recovered)' }}>◀ bridge</span>}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className="num-figure" style={{ fontWeight: 600 }}>{formatUSD(s.amount_usd)}</span>
              <span className={`disposition-tag ${s.status || 'explained'}`}>
                {s.status === 'escalated' ? '! escalated' : s.status === 'recovered' ? '↑ recovered' : '✓ explained'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlaceholderResidualWaterfall({ openingDeviation = 44000, factors = [], residual = 5000, recoveryFindings = [] }) {
  const displayFactors = factors.length > 0 ? factors : CANONICAL_FACTORS;
  const displayRecovery = recoveryFindings.length > 0 ? recoveryFindings : CANONICAL_RECOVERY;

  return (
    <div className="placeholder-stub" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="placeholder-header">
        <span>Act II Stepped Waterfall (descending variance decomposition)</span>
        <span className="num-figure">Opening: {formatUSD(openingDeviation)}</span>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div className="waterfall-stepped-list">
          <div className="waterfall-step" style={{ borderLeftColor: 'var(--color-border-strong)' }}>
            <span>Opening deviation (8.41% vs 10.00%)</span>
            <span className="num-figure" style={{ fontWeight: 700 }}>{formatUSD(openingDeviation)}</span>
          </div>
          {displayFactors.map((f, idx) => (
            <div
              key={idx}
              className={`waterfall-step ${f.status === 'rejected' ? 'rejected' : ''}`}
              style={{
                borderLeftColor: f.status === 'rejected' ? 'var(--color-border)' : 'var(--color-explained)'
              }}
            >
              <div>
                <span>{f.status === 'rejected' ? '✗' : '├─'} {formatUSD(f.factor_usd)} {f.label}</span>
                {f.title && <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginLeft: '6px' }}>({f.title})</span>}
              </div>
              <span className="num-figure" style={{ color: f.status === 'rejected' ? 'var(--color-text-muted)' : 'var(--color-text-secondary)' }}>
                {f.residual_after !== undefined ? `rem: ${formatUSD(f.residual_after)}` : ''}
              </span>
            </div>
          ))}
          <div className="waterfall-step escalate">
            <span>ESCALATE (Unresolved residual, billing-run config gap)</span>
            <span className="num-figure" style={{ fontWeight: 700 }}>{formatUSD(residual)}</span>
          </div>
        </div>

        {displayRecovery.length > 0 && (
          <div className="recovery-box">
            <div>
              <span style={{ fontWeight: 600 }}>+{formatUSD(displayRecovery[0].entitlement_impact_usd)}</span>
              <span style={{ marginLeft: '8px', fontSize: '12px' }}>{displayRecovery[0].label}</span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>recovered entitlement</span>
          </div>
        )}
      </div>
    </div>
  );
}

function PlaceholderEvidenceCard({ factor, onClose }) {
  if (!factor) return null;
  return (
    <div className="placeholder-stub" style={{ margin: '8px 0' }}>
      <div className="placeholder-header">
        <span>Evidence Card: {factor.cause_id || factor.label}</span>
        {onClose && <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }}>✕</button>}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '4px', fontSize: '12px' }}>
        <span style={{ color: 'var(--color-text-secondary)' }}>Classification:</span>
        <span className="num-figure">{factor.classification || 'TIMING'}</span>
        <span style={{ color: 'var(--color-text-secondary)' }}>Amount:</span>
        <span className="num-figure">{formatUSD(factor.factor_usd || factor.amount_usd)}</span>
        <span style={{ color: 'var(--color-text-secondary)' }}>Transactions:</span>
        <span className="num-figure">{factor.transaction_ids?.join(', ') || 'None'}</span>
        <span style={{ color: 'var(--color-text-secondary)' }}>Evidence Refs:</span>
        <span className="num-figure">{factor.evidence_refs?.join(', ') || 'None'}</span>
        <span style={{ color: 'var(--color-text-secondary)' }}>AO Message ID:</span>
        <span className="num-figure">{factor.ao_message_id || 'N/A'}</span>
      </div>
    </div>
  );
}

function PlaceholderApprovalModal({ escalationPacket, isOpen, onApprove, onReject }) {
  if (!isOpen) return null;
  const p = escalationPacket || CANONICAL_ESCALATION;
  const lines = p.proposed_journal_entry?.lines || [];

  return (
    <div className="modal-overlay">
      <div className="modal-dialog">
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontWeight: 600, fontSize: '13px' }}>Draft True-Up Journal Entry</span>
            <span className="num-figure" style={{ color: 'var(--color-escalated)', fontSize: '12px' }}>
              {formatUSD(p.residual_usd)}
            </span>
          </div>
          <span className="num-figure" style={{ color: 'var(--color-text-muted)', fontSize: '11px' }}>
            {p.escalation_id}
          </span>
        </div>
        <div className="modal-body">
          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
              Probable Cause & Confidence
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-primary)' }}>
              {p.probable_cause}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-escalated)', marginBottom: '4px' }}>
              Missing Evidence Gap
            </div>
            <ul style={{ paddingLeft: '18px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              {p.evidence_gap?.map((gap, i) => (
                <li key={i}>{gap}</li>
              ))}
            </ul>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginBottom: '6px' }}>
              Proposed Journal Lines (AO Ledger: {p.ao_ledger_reference})
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', fontFamily: 'var(--font-figures)' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)' }}>
                  <th style={{ padding: '4px' }}>Entity</th>
                  <th style={{ padding: '4px' }}>Account</th>
                  <th style={{ padding: '4px' }}>Description</th>
                  <th style={{ padding: '4px', textAlign: 'right' }}>Debit</th>
                  <th style={{ padding: '4px', textAlign: 'right' }}>Credit</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: '4px' }}>{line.entity}</td>
                    <td style={{ padding: '4px' }}>{line.account}</td>
                    <td style={{ padding: '4px' }}>{line.description}</td>
                    <td style={{ padding: '4px', textAlign: 'right' }}>{line.debit ? formatUSD(line.debit) : '—'}</td>
                    <td style={{ padding: '4px', textAlign: 'right' }}>{line.credit ? formatUSD(line.credit) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onReject}>
            Reject
          </button>
          <button className="btn-primary" onClick={onApprove}>
            Approve true-up
          </button>
        </div>
      </div>
    </div>
  );
}

function PlaceholderCostMeter({ costSummary }) {
  const summary = costSummary || { fast_calls: 6, strong_calls: 4, estimated_cost_usd: 0.18 };
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontFamily: 'var(--font-figures)' }}>
      <span>Fast {summary.fast_calls}</span>
      <span style={{ color: 'var(--color-text-muted)' }}>·</span>
      <span>Strong {summary.strong_calls}</span>
      <span style={{ color: 'var(--color-text-muted)' }}>·</span>
      <span style={{ color: 'var(--color-text-secondary)' }}>${summary.estimated_cost_usd?.toFixed ? summary.estimated_cost_usd.toFixed(2) : summary.estimated_cost_usd}</span>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Component Resolution (Parallel Worker Components or Fallback Stubs)
// -----------------------------------------------------------------------------

const TraceStream = componentModules['./components/TraceStream.jsx']?.default || PlaceholderTraceStream;
const StrataColumn = componentModules['./components/StrataColumn.jsx']?.default || PlaceholderStrataColumn;
const ResidualWaterfall = componentModules['./components/ResidualWaterfall.jsx']?.default || PlaceholderResidualWaterfall;
const EvidenceCard = componentModules['./components/EvidenceCard.jsx']?.default || PlaceholderEvidenceCard;
const ApprovalModal = componentModules['./components/ApprovalModal.jsx']?.default || PlaceholderApprovalModal;
const CostMeter = componentModules['./components/CostMeter.jsx']?.default || PlaceholderCostMeter;

// -----------------------------------------------------------------------------
// App Shell
// -----------------------------------------------------------------------------

export default function App() {
  const [events, setEvents] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [activeToggle, setActiveToggle] = useState('Close'); // 'Excavate' | 'Close'
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [approvalDecision, setApprovalDecision] = useState(null); // 'APPROVED' | 'REJECTED' | null
  const [selectedFactor, setSelectedFactor] = useState(null);

  // Derived state from events or canonical baseline
  const [strata, setStrata] = useState(CANONICAL_STRATA);
  const [factors, setFactors] = useState(CANONICAL_FACTORS);
  const [recoveryFindings, setRecoveryFindings] = useState(CANONICAL_RECOVERY);
  const [openingDeviation, setOpeningDeviation] = useState(44000);
  const [residual, setResidual] = useState(5000);
  const [costSummary, setCostSummary] = useState({
    fast_calls: 6,
    strong_calls: 4,
    estimated_cost_usd: 0.18
  });
  const [escalationPacket, setEscalationPacket] = useState(CANONICAL_ESCALATION);
  const [aoProcessId, setAoProcessId] = useState('ao-reconfx-2026-03');
  const [neatlogsTraceUrl, setNeatlogsTraceUrl] = useState('https://neatlogs.com/traces/tr-recon-20260331-01');

  // WebSocket Connection to Backend ws://localhost:8000/ws/events
  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;
    let isDisposed = false;

    function connectWs() {
      try {
        ws = new WebSocket('ws://localhost:8000/ws/events');

        ws.onopen = () => {
          if (!isDisposed) {
            setWsConnected(true);
          }
        };

        ws.onmessage = (eventMsg) => {
          if (isDisposed) return;
          try {
            const parsed = JSON.parse(eventMsg.data);
            setEvents((prev) => [...prev, parsed]);

            // Feed events to state
            if (parsed.event_type === 'COST' && parsed.payload) {
              setCostSummary(parsed.payload);
            } else if (parsed.event_type === 'ESCALATION' && parsed.payload) {
              setEscalationPacket((prev) => ({ ...prev, ...parsed.payload }));
              if (parsed.payload.residual_usd !== undefined) {
                setResidual(parsed.payload.residual_usd);
              }
            } else if (parsed.event_type === 'FACTOR_ACCEPTED' && parsed.payload) {
              if (parsed.payload.residual_after !== undefined) {
                setResidual(parsed.payload.residual_after);
              }
            }
            if (parsed.payload?.ao_process_id) {
              setAoProcessId(parsed.payload.ao_process_id);
            }
            if (parsed.payload?.neatlogs_trace_url) {
              setNeatlogsTraceUrl(parsed.payload.neatlogs_trace_url);
            }
          } catch (err) {
            console.error('Error processing event message:', err);
          }
        };

        ws.onclose = () => {
          if (!isDisposed) {
            setWsConnected(false);
            reconnectTimeout = setTimeout(connectWs, 3000);
          }
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch (e) {
        if (!isDisposed) {
          setWsConnected(false);
          reconnectTimeout = setTimeout(connectWs, 3000);
        }
      }
    }

    connectWs();

    return () => {
      isDisposed = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  const handleApprove = () => {
    setApprovalDecision('APPROVED');
    setIsApprovalOpen(false);
    try {
      fetch('http://localhost:8000/api/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          escalation_id: escalationPacket?.escalation_id || 'ESC-2026-03-001',
          decision: 'APPROVE',
          actor: 'controller',
          notes: 'Approved true-up from controller console',
        }),
      }).catch((err) => console.warn('Approval sync failed:', err));
    } catch (e) {
      console.warn('Approval fetch error:', e);
    }
  };

  const handleReject = () => {
    setApprovalDecision('REJECTED');
    setIsApprovalOpen(false);
    try {
      fetch('http://localhost:8000/api/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          escalation_id: escalationPacket?.escalation_id || 'ESC-2026-03-001',
          decision: 'REJECT',
          actor: 'controller',
          notes: 'Rejected true-up from controller console',
        }),
      }).catch((err) => console.warn('Reject sync failed:', err));
    } catch (e) {
      console.warn('Reject fetch error:', e);
    }
  };

  return (
    <div className="app-shell">
      {/* Header: entity/period title, AO process ID + Neatlogs trace link placeholders, Excavate|Close toggle */}
      <header className="app-header">
        <div className="header-meta">
          <div className="header-title-row">
            <span className="entity-pair-title">ENT-IN-02 → ENT-US-01</span>
            <span className="period-badge">March 2026 close</span>
          </div>
          <div className="header-traces-row">
            <div className="trace-item">
              <span className="trace-label">AO process:</span>
              <span className="trace-val">{aoProcessId}</span>
            </div>
            <span>·</span>
            <div className="trace-item">
              <span className="trace-label">Neatlogs trace:</span>
              <a
                href={neatlogsTraceUrl}
                target="_blank"
                rel="noreferrer"
                className="trace-link"
              >
                {neatlogsTraceUrl.split('/').pop()}
              </a>
            </div>
          </div>
        </div>

        <div className="header-actions">
          <div className="ws-status-indicator" title={wsConnected ? 'Connected to ws://localhost:8000/ws/events' : 'Reconnecting to ws://localhost:8000/ws/events'}>
            <span className={`ws-dot ${wsConnected ? 'connected' : 'disconnected'}`} />
            <span>{wsConnected ? 'live stream' : 'offline / local fixture'}</span>
          </div>

          <div className="view-toggle-group" role="group" aria-label="View toggle">
            <button
              className={`view-toggle-btn ${activeToggle === 'Excavate' ? 'active' : ''}`}
              onClick={() => setActiveToggle('Excavate')}
            >
              Excavate
            </button>
            <button
              className={`view-toggle-btn ${activeToggle === 'Close' ? 'active' : ''}`}
              onClick={() => setActiveToggle('Close')}
            >
              Close
            </button>
          </div>
        </div>
      </header>

      {/* Two-Column Body: left Trace Stream, right Act I StrataColumn + Act II ResidualWaterfall */}
      <main className="app-body">
        {/* Left Column: Trace Stream Area */}
        <section className="trace-panel-container">
          <div className="panel-header">
            <span className="panel-header-title">Agent Trace</span>
            <span className="num-figure" style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              ReAct loop
            </span>
          </div>
          <div className="panel-content-scroll">
            <TraceStream events={events} />
            {selectedFactor && (
              <EvidenceCard factor={selectedFactor} onClose={() => setSelectedFactor(null)} />
            )}
          </div>
        </section>

        {/* Right Column: Act I & Act II */}
        <section className="acts-column-container">
          {/* Act I: The Clearing Account */}
          <div className="act-section act-one">
            <div className="act-header">
              <div className="act-title-group">
                <span className="act-title">Act I — The Clearing Account</span>
                <span className="act-summary-figure">1900 · $1,847,000 · 38 months</span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Depth: geological strata</span>
            </div>
            <div className="act-content-area">
              <StrataColumn strata={strata} onSelectStratum={setSelectedFactor} />
            </div>
          </div>

          {/* Act II: This Month */}
          <div className="act-section act-two">
            <div className="act-header">
              <div className="act-title-group">
                <span className="act-title">Act II — This Month</span>
                <span className="act-summary-figure">Opening variance $44,000</span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Descending waterfall</span>
            </div>
            <div className="act-content-area">
              <ResidualWaterfall
                openingDeviation={openingDeviation}
                factors={factors}
                residual={residual}
                recoveryFindings={recoveryFindings}
                onSelectFactor={setSelectedFactor}
              />
            </div>
          </div>
        </section>
      </main>

      {/* Footer Bar: CostMeter + Review Escalation Action */}
      <footer className="app-footer">
        <div className="footer-cost-area">
          <CostMeter costSummary={costSummary} />
        </div>

        <div className="footer-actions-area">
          {approvalDecision ? (
            <span
              className="num-figure"
              style={{
                color: approvalDecision === 'APPROVED' ? 'var(--color-explained)' : 'var(--color-escalated)',
                fontWeight: 600,
                fontSize: '12px'
              }}
            >
              {approvalDecision === 'APPROVED' ? 'True-up approved.' : 'True-up rejected.'}
            </span>
          ) : (
            <button
              className="btn-escalation-review"
              onClick={() => setIsApprovalOpen(true)}
            >
              Review escalation
            </button>
          )}
        </div>
      </footer>

      {/* Approval Modal */}
      <ApprovalModal
        escalationPacket={escalationPacket}
        isOpen={isApprovalOpen}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </div>
  );
}
