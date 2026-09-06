import React, { useMemo } from 'react';

/**
 * Helper to format dollar amounts with comma grouping.
 */
function formatUSD(amount) {
  const num = Number(amount);
  if (isNaN(num)) return '$0';
  return '$' + Math.round(num).toLocaleString('en-US');
}

/**
 * ResidualWaterfall
 *
 * Act II's stepped descent from the opening margin deviation ($44,000)
 * down through each accepted factor to the final residual ($5,000).
 * Any rejected hypothesis (accepted: false) is rendered as a struck-through step.
 * Recovery findings render as a visually distinct separate card/axis.
 *
 * Props:
 *  - openingDeviation: number (default: 44000)
 *  - factors: Array<{ cause_id, label, classification, factor_usd, accepted, rejection_reason, ... }>
 *  - residual: number (default: 5000)
 *  - recoveryFindings: Array<{ label, amount_usd, entitlement_impact_usd, proposed_entry, ... }>
 */
export default function ResidualWaterfall({
  openingDeviation = 44000,
  factors = [],
  residual = 5000,
  recoveryFindings = [],
}) {
  // Compute stepped descent items
  const { steps, finalCalculatedResidual } = useMemo(() => {
    let currentBalance = Number(openingDeviation) || 44000;
    const computedSteps = [];

    (factors || []).forEach((factor, index) => {
      const amt = Number(factor.factor_usd) || 0;
      const isAccepted = factor.accepted !== false;
      const priorBalance = currentBalance;

      if (isAccepted) {
        currentBalance -= amt;
      }

      computedSteps.push({
        id: factor.cause_id || `factor-${index}`,
        factor,
        priorBalance,
        currentBalance,
        reductionUsd: amt,
        accepted: isAccepted,
      });
    });

    return {
      steps: computedSteps,
      finalCalculatedResidual: currentBalance,
    };
  }, [openingDeviation, factors]);

  // Displayed final residual
  const displayResidual = residual != null ? residual : finalCalculatedResidual;

  return (
    <div className="waterfall-container" aria-label="Act II Margin Decomposition Waterfall">
      <style>{`
        .waterfall-container {
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

        .waterfall-header {
          padding: 12px 16px;
          border-bottom: 1px solid #21262d;
          background: #161b22;
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          flex-wrap: wrap;
          gap: 8px;
        }

        .waterfall-header-title {
          font-size: 11px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: #8b949e;
          font-weight: 600;
        }

        .waterfall-header-baseline {
          font-family: var(--font-figures, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-variant-numeric: tabular-nums;
          font-size: 13px;
          color: #f0f6fc;
          font-weight: 600;
        }

        .waterfall-body {
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          background: #090d12;
        }

        /* Stepped descent tree */
        .descent-tree {
          display: flex;
          flex-direction: column;
          position: relative;
        }

        .descent-node {
          display: flex;
          align-items: stretch;
          position: relative;
          min-height: 48px;
          animation: waterfallStep 0.2s ease-out forwards;
        }

        @keyframes waterfallStep {
          from {
            opacity: 0;
            transform: translateY(-4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .descent-rail {
          display: flex;
          flex-direction: column;
          align-items: center;
          width: 90px;
          flex-shrink: 0;
          position: relative;
        }

        .balance-pill {
          font-family: var(--font-figures, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-variant-numeric: tabular-nums;
          font-size: 13px;
          font-weight: 700;
          color: #f0f6fc;
          background: #161b22;
          border: 1px solid #30363d;
          padding: 4px 8px;
          border-radius: 3px;
          width: 72px;
          text-align: right;
          z-index: 2;
        }

        .rail-vertical-line {
          width: 2px;
          background: #30363d;
          flex: 1;
          margin-top: -2px;
          margin-bottom: -2px;
          z-index: 1;
        }

        .descent-branch {
          flex: 1;
          display: flex;
          align-items: center;
          padding: 6px 12px;
          margin-left: 8px;
          border-radius: 3px;
          background: #11161d;
          border: 1px solid #21262d;
          box-sizing: border-box;
          gap: 12px;
        }

        .descent-branch.accepted-step {
          border-left: 3px solid var(--color-explained, #3b82f6);
        }

        .descent-branch.rejected-step {
          border-left: 3px solid #484f58;
          background: #0d1117;
          opacity: 0.65;
        }

        .descent-branch.residual-step {
          border-left: 3px solid var(--color-escalated, #ef4444);
          background: rgba(239, 68, 68, 0.08);
          border-color: rgba(239, 68, 68, 0.3);
        }

        .step-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }

        .step-title-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .step-cause-id {
          font-family: var(--font-trace, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-size: 10px;
          font-weight: 700;
          color: #8b949e;
        }

        .step-label {
          font-size: 12px;
          font-weight: 600;
          color: #f0f6fc;
        }

        .step-subtext {
          font-size: 11px;
          color: #8b949e;
        }

        .struck-through {
          text-decoration: line-through;
          color: #6e7681 !important;
        }

        .step-amount-col {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 2px;
          flex-shrink: 0;
        }

        .step-reduction-amount {
          font-family: var(--font-figures, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-variant-numeric: tabular-nums;
          font-size: 13px;
          font-weight: 700;
        }

        .step-reduction-amount.accepted {
          color: var(--color-explained, #58a6ff);
        }

        .step-badge {
          font-family: var(--font-trace, monospace);
          font-size: 9px;
          font-weight: 700;
          letter-spacing: 0.05em;
          padding: 1px 5px;
          border-radius: 2px;
          text-transform: uppercase;
        }

        .badge-explained {
          background: rgba(59, 130, 246, 0.18);
          color: var(--color-explained, #58a6ff);
          border: 1px solid rgba(59, 130, 246, 0.4);
        }

        .badge-rejected {
          background: rgba(110, 118, 129, 0.18);
          color: #8b949e;
          border: 1px solid #484f58;
        }

        .badge-escalated {
          background: rgba(239, 68, 68, 0.2);
          color: var(--color-escalated, #f85149);
          border: 1px solid rgba(239, 68, 68, 0.5);
        }

        /* Recovery Finding: Visually distinct separate card/axis */
        .recovery-axis-card {
          border: 1px solid var(--color-recovered, #10b981);
          border-left-width: 4px;
          background: rgba(16, 185, 129, 0.06);
          border-radius: 4px;
          padding: 12px 16px;
          display: flex;
          flex-direction: column;
          gap: 6px;
          animation: waterfallStep 0.2s ease-out forwards;
        }

        .recovery-axis-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 10px;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          font-family: var(--font-trace, monospace);
          color: var(--color-recovered, #3fb950);
          font-weight: 700;
        }

        .recovery-axis-body {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          flex-wrap: wrap;
          gap: 8px;
        }

        .recovery-title {
          font-size: 13px;
          font-weight: 600;
          color: #f0f6fc;
        }

        .recovery-amount {
          font-family: var(--font-figures, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-variant-numeric: tabular-nums;
          font-size: 16px;
          font-weight: 700;
          color: var(--color-recovered, #3fb950);
        }

        .recovery-footer {
          font-size: 11px;
          color: #8b949e;
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-top: 1px solid rgba(16, 185, 129, 0.2);
          padding-top: 6px;
        }
      `}</style>

      {/* Act II Header */}
      <div className="waterfall-header">
        <div className="waterfall-header-title">
          ACT II · Current Close Causal Decomposition (March 2026)
        </div>
        <div className="waterfall-header-baseline">
          Opening Δ₀: {formatUSD(openingDeviation)} · Residual: {formatUSD(displayResidual)}
        </div>
      </div>

      <div className="waterfall-body">
        {/* Stepped Descent */}
        <div className="descent-tree" role="region" aria-label="Residual reduction descent">
          {/* Level 0: Opening Deviation */}
          <div className="descent-node">
            <div className="descent-rail">
              <div className="balance-pill">{formatUSD(openingDeviation)}</div>
              <div className="rail-vertical-line" />
            </div>
            <div className="descent-branch">
              <div className="step-content">
                <div className="step-title-row">
                  <span className="step-cause-id">Δ₀</span>
                  <span className="step-label">Opening Margin Shortfall</span>
                </div>
                <div className="step-subtext">
                  Recognised markup 8.41% vs contractual target 10.00% on $2,760,000 base
                </div>
              </div>
              <div className="step-amount-col">
                <span className="step-badge badge-escalated">UNEXPLAINED</span>
              </div>
            </div>
          </div>

          {/* Stepped Factor Reductions & Struck-Through Rejections */}
          {steps.map((step) => {
            const { id, factor, currentBalance, reductionUsd, accepted } = step;

            return (
              <div key={id} className="descent-node">
                <div className="descent-rail">
                  <div className="balance-pill">{formatUSD(currentBalance)}</div>
                  <div className="rail-vertical-line" />
                </div>

                <div className={`descent-branch ${accepted ? 'accepted-step' : 'rejected-step'}`}>
                  <div className="step-content">
                    <div className="step-title-row">
                      <span className="step-cause-id">{factor.cause_id || 'FX'}</span>
                      <span className={`step-label ${accepted ? '' : 'struck-through'}`}>
                        {factor.label || factor.classification}
                      </span>
                    </div>
                    <div className={`step-subtext ${accepted ? '' : 'struck-through'}`}>
                      {accepted
                        ? factor.classification === 'TIMING_UNBILLED'
                          ? 'Off-cycle payroll posted post-cutoff · Roll forward to April billing'
                          : factor.classification === 'APPROVED_EXCLUSION'
                          ? 'Severance excluded by memo EXP-2026-08 · Precedence overrides GL mapping'
                          : 'Factor substantiated by documentation'
                        : factor.rejection_reason || 'Below $500 materiality threshold · Logged & rejected'}
                    </div>
                  </div>

                  <div className="step-amount-col">
                    <div
                      className={`step-reduction-amount ${accepted ? 'accepted' : 'struck-through'}`}
                    >
                      {accepted ? `-${formatUSD(reductionUsd)}` : formatUSD(reductionUsd)}
                    </div>
                    <span className={`step-badge ${accepted ? 'badge-explained' : 'badge-rejected'}`}>
                      {accepted ? 'EXPLAINED' : 'REJECTED'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Final Residual Node */}
          <div className="descent-node">
            <div className="descent-rail">
              <div className="balance-pill" style={{ borderColor: 'var(--color-escalated, #ef4444)' }}>
                {formatUSD(displayResidual)}
              </div>
            </div>

            <div className="descent-branch residual-step">
              <div className="step-content">
                <div className="step-title-row">
                  <span className="step-cause-id" style={{ color: 'var(--color-escalated, #f85149)' }}>
                    RESIDUAL
                  </span>
                  <span className="step-label">Unsubstantiated Margin Residual</span>
                </div>
                <div className="step-subtext">
                  Effective rate applied 9.79% vs 10.00% · Missing March 2026 billing config export
                </div>
              </div>

              <div className="step-amount-col">
                <div className="step-reduction-amount" style={{ color: 'var(--color-escalated, #f85149)' }}>
                  {formatUSD(displayResidual)}
                </div>
                <span className="step-badge badge-escalated">ESCALATE</span>
              </div>
            </div>
          </div>
        </div>

        {/* Visually Distinct Separate Card/Axis: Recovery Findings */}
        <div className="recovery-axis-card" role="region" aria-label="Independent recovery axis">
          <div className="recovery-axis-header">
            <span>Independent Recovery Axis (Separate Finding)</span>
            <span className="step-badge" style={{ background: 'rgba(16, 185, 129, 0.2)', color: 'var(--color-recovered, #3fb950)', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
              RECOVERED
            </span>
          </div>

          <div className="recovery-axis-body">
            <div className="recovery-title">
              {recoveryFindings && recoveryFindings.length > 0
                ? recoveryFindings[0].label || 'Recovered Entitlement'
                : 'Recovered Entitlement — Misclassified Rechargeable Software'}
            </div>
            <div className="recovery-amount">
              {recoveryFindings && recoveryFindings.length > 0
                ? `+${formatUSD(recoveryFindings[0].entitlement_impact_usd || 14000)}`
                : '+$14,000'}
            </div>
          </div>

          <div className="recovery-footer">
            <span>
              $140,000 engineering SaaS stranded in excluded GL 6800 · Reclass to 6100 @ 10% markup
            </span>
            <span style={{ fontFamily: 'var(--font-trace, monospace)', fontSize: '10px' }}>
              Action: Draft GL reclassification + April billing
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export { ResidualWaterfall };
