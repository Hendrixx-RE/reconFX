import React from 'react';

/**
 * Format cost into dollar string or fallback $0.--
 */
function formatCost(cost) {
  if (cost == null) return '$0.--';
  if (typeof cost === 'string') {
    return cost.startsWith('$') ? cost : `$${cost}`;
  }
  const num = Number(cost);
  if (isNaN(num)) return '$0.--';
  return `$${num.toFixed(2)}`;
}

/**
 * CostMeter
 *
 * A quiet footer-bar element showing Tensormux route call counts
 * and estimated cost for the forensic investigation.
 * Format per README §6.5: "Fast: 6 calls · Strong: 4 calls · $0.--"
 *
 * Props:
 *  - costSummary: { fast_calls?: number, strong_calls?: number, estimated_cost_usd?: number | string }
 */
export default function CostMeter({ costSummary = {} }) {
  const {
    fast_calls = 6,
    strong_calls = 4,
    estimated_cost_usd,
  } = costSummary || {};

  const costDisplay = formatCost(estimated_cost_usd);

  return (
    <div className="cost-meter-bar" aria-label="Investigation compute and cost summary">
      <style>{`
        .cost-meter-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 6px 14px;
          background: #0d1117;
          border: 1px solid #21262d;
          border-radius: 4px;
          color: #8b949e;
          font-size: 11px;
          box-sizing: border-box;
          width: 100%;
          user-select: none;
        }

        .cost-meter-main {
          display: flex;
          align-items: center;
          gap: 6px;
          font-family: var(--font-trace, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
        }

        .cost-meter-segment {
          display: inline-flex;
          align-items: baseline;
          gap: 3px;
        }

        .cost-meter-figure {
          font-family: var(--font-figures, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-variant-numeric: tabular-nums;
          font-weight: 600;
          color: #c9d1d9;
        }

        .cost-meter-cost {
          font-family: var(--font-figures, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
          font-variant-numeric: tabular-nums;
          font-weight: 700;
          color: #f0f6fc;
        }

        .cost-meter-dot {
          color: #484f58;
        }

        .cost-meter-benchmark {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 10px;
          color: #6e7681;
          font-family: var(--font-trace, monospace);
        }

        .cost-meter-tag {
          color: #484f58;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
      `}</style>

      <div className="cost-meter-main">
        <span className="cost-meter-segment">
          Fast: <span className="cost-meter-figure">{fast_calls}</span> calls
        </span>
        <span className="cost-meter-dot">·</span>
        <span className="cost-meter-segment">
          Strong: <span className="cost-meter-figure">{strong_calls}</span> calls
        </span>
        <span className="cost-meter-dot">·</span>
        <span className="cost-meter-cost">{costDisplay}</span>
      </div>

      <div className="cost-meter-benchmark">
        <span className="cost-meter-tag">Tensormux</span>
        <span className="cost-meter-dot">·</span>
        <span>vs. 4–8 hrs manual investigation</span>
      </div>
    </div>
  );
}

export { CostMeter };
