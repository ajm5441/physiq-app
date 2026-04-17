// src/components/UI.jsx
// Shared primitive components used across all pages.

import styles from './UI.module.css';

// ── Button ────────────────────────────────────────────────────────────────────
export function Button({
  children, onClick, variant = 'primary', size = 'md',
  disabled = false, loading = false, type = 'button', className = '',
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${styles.btn} ${styles[`btn-${variant}`]} ${styles[`btn-${size}`]} ${className}`}
    >
      {loading ? <span className={styles.btnSpinner} /> : children}
    </button>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, className = '', glow = false, onClick }) {
  return (
    <div
      className={`${styles.card} ${glow ? styles.cardGlow : ''} ${onClick ? styles.cardClickable : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────
export function Badge({ children, variant = 'default' }) {
  return (
    <span className={`${styles.badge} ${styles[`badge-${variant}`]}`}>
      {children}
    </span>
  );
}

// ── ProgressBar ───────────────────────────────────────────────────────────────
export function ProgressBar({ value, max = 100, variant = 'amber', label }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className={styles.progressWrap}>
      {label && (
        <div className={styles.progressLabel}>
          <span>{label}</span>
          <span className={styles.progressPct}>{pct}%</span>
        </div>
      )}
      <div className={styles.progressTrack}>
        <div
          className={`${styles.progressFill} ${styles[`progress-${variant}`]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── TierIndicator ─────────────────────────────────────────────────────────────
// Shows the four tiers as pips — filled up to currentTier.
export function TierIndicator({ currentTier, tierCorrect = {} }) {
  return (
    <div className={styles.tierWrap}>
      <span className={styles.tierLabel}>TIER</span>
      {[1, 2, 3, 4].map(t => (
        <div
          key={t}
          className={`${styles.tierPip} ${t < currentTier ? styles.tierDone : ''} ${t === currentTier ? styles.tierActive : ''}`}
          title={`Tier ${t}: ${tierCorrect[t] || 0}/2 correct`}
        >
          <span className={styles.tierNum}>{t}</span>
          <div className={styles.tierDots}>
            <div className={`${styles.tierDot} ${(tierCorrect[t] || 0) >= 1 ? styles.tierDotFilled : ''}`} />
            <div className={`${styles.tierDot} ${(tierCorrect[t] || 0) >= 2 ? styles.tierDotFilled : ''}`} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── QuestionCounter ───────────────────────────────────────────────────────────
export function QuestionCounter({ used, total = 12 }) {
  const remaining = total - used;
  const danger    = remaining <= 3;
  return (
    <div className={`${styles.qCounter} ${danger ? styles.qCounterDanger : ''}`}>
      <span className={styles.qCounterNum}>{remaining}</span>
      <span className={styles.qCounterLabel}>remaining</span>
    </div>
  );
}

// ── Loader ────────────────────────────────────────────────────────────────────
export function Loader({ size = 'md', label = 'Loading…' }) {
  return (
    <div className={`${styles.loader} ${styles[`loader-${size}`]}`} role="status">
      <div className={styles.loaderRing} />
      {label && <span className={styles.loaderLabel}>{label}</span>}
    </div>
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, body, action }) {
  return (
    <div className={styles.empty}>
      {icon && <div className={styles.emptyIcon}>{icon}</div>}
      <h3 className={styles.emptyTitle}>{title}</h3>
      {body && <p className={styles.emptyBody}>{body}</p>}
      {action && <div className={styles.emptyAction}>{action}</div>}
    </div>
  );
}

// ── StatusDot ─────────────────────────────────────────────────────────────────
export function StatusDot({ status }) {
  const map = {
    locked:   'muted',
    unlocked: 'amber',
    passed:   'green',
    skipped:  'blue',
  };
  return <span className={`${styles.statusDot} ${styles[`dot-${map[status] || 'muted'}`]}`} />;
}
