// src/pages/DashboardPage.jsx
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useDashboard } from '../hooks/index';
import {
  Card, Badge, ProgressBar, StatusDot, Loader, Button, EmptyState
} from '../components/UI';
import styles from './DashboardPage.module.css';

// ── Topic score card ──────────────────────────────────────────────────────────
function TopicCard({ topic, onClick }) {
  const { name, status, total_score, subtopics_passed, subtopics_total,
          bonus_unlocked, bonus_completed } = topic;

  const locked    = status === 'locked';
  const completed = status === 'completed';
  const pct       = subtopics_total > 0
    ? Math.round((subtopics_passed / subtopics_total) * 100) : 0;

  return (
    <Card
      className={`${styles.topicCard} ${locked ? styles.topicLocked : ''}`}
      onClick={locked ? undefined : onClick}
      glow={status === 'unlocked' && subtopics_passed > 0}
    >
      <div className={styles.topicHeader}>
        <span className={styles.topicName}>{name}</span>
        <div className={styles.topicBadges}>
          {completed   && <Badge variant="green">Complete</Badge>}
          {locked      && <Badge variant="default">Locked</Badge>}
          {bonus_unlocked && !bonus_completed &&
            <Badge variant="amber">Bonus!</Badge>}
          {bonus_completed && <Badge variant="teal">Bonus ✓</Badge>}
        </div>
      </div>

      <div className={styles.topicScore}>
        {locked ? '—' : total_score.toLocaleString()}
        {!locked && <span className={styles.topicScoreLabel}>pts</span>}
      </div>

      <ProgressBar
        value={subtopics_passed}
        max={subtopics_total || 1}
        variant={completed ? 'green' : locked ? 'amber' : 'amber'}
      />

      <div className={styles.topicMeta}>
        <span className={styles.topicMetaText}>
          {locked ? 'Complete previous topic' :
            `${subtopics_passed} / ${subtopics_total} subtopics`}
        </span>
      </div>
    </Card>
  );
}

// ── Strength / weakness row ───────────────────────────────────────────────────
function SubtopicRow({ name, score, variant }) {
  return (
    <div className={styles.subtopicRow}>
      <StatusDot status={variant === 'strong' ? 'passed' : 'locked'} />
      <span className={styles.subtopicName}>{name}</span>
      <span className={`${styles.subtopicScore} ${variant === 'strong' ? styles.scoreStrong : styles.scoreWeak}`}>
        {score}
      </span>
    </div>
  );
}

// ── Dashboard page ────────────────────────────────────────────────────────────
export function DashboardPage() {
  const { user }                      = useAuth();
  const { data, loading, error }      = useDashboard();
  const navigate                      = useNavigate();

  if (loading) return <Loader size="lg" label="Fetching telemetry…" />;
  if (error)   return (
    <EmptyState icon="⚠" title="Failed to load dashboard" body={error} />
  );
  if (!data)   return null;

  const {
    overall_score, subtopics_passed, subtopics_skipped,
    bonus_unlocked, avg_session_score,
    topics, strong_areas, weak_areas, next_subtopic,
  } = data;

  return (
    <div className={styles.page}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Mission Control</h1>
          <p className={styles.pageSubtitle}>
            <span className={styles.mono}>{user?.username}</span>
            {' '}· Physics I
          </p>
        </div>
        {next_subtopic && (
          <Button
            onClick={() => navigate(`/session/${next_subtopic.subtopic_id}`)}
            size="lg"
          >
            Continue → {next_subtopic.name}
          </Button>
        )}
      </div>

      {/* ── Stat row ───────────────────────────────────────────────────────── */}
      <div className={styles.statRow}>
        {[
          { label: 'Total score',      value: overall_score?.toLocaleString() ?? '0' },
          { label: 'Subtopics passed', value: subtopics_passed ?? 0 },
          { label: 'Subtopics skipped',value: subtopics_skipped ?? 0 },
          { label: 'Bonus topics',     value: bonus_unlocked ?? 0 },
          { label: 'Avg session score',value: `${avg_session_score ?? 0}%` },
        ].map(({ label, value }) => (
          <div key={label} className={styles.statCard}>
            <span className={styles.statVal}>{value}</span>
            <span className={styles.statLabel}>{label}</span>
          </div>
        ))}
      </div>

      {/* ── Topic grid ─────────────────────────────────────────────────────── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Topic Overview</h2>
        <div className={styles.topicGrid}>
          {(topics || []).map(t => (
            <TopicCard
              key={t.topic_id}
              topic={t}
              onClick={() => navigate(`/topics/${t.topic_id}`)}
            />
          ))}
        </div>
      </section>

      {/* ── Strengths / Weaknesses ─────────────────────────────────────────── */}
      <div className={styles.twoCol}>
        <section className={styles.panel}>
          <h2 className={styles.panelTitle}>
            <span className={styles.panelDot} style={{ background: 'var(--green)' }} />
            Strong Areas
          </h2>
          {(strong_areas || []).length === 0
            ? <p className={styles.panelEmpty}>Keep studying to identify strengths</p>
            : (strong_areas || []).map(s => (
                <SubtopicRow key={s.subtopic_id}
                  name={s.name} score={s.best_score} variant="strong" />
              ))
          }
        </section>

        <section className={styles.panel}>
          <h2 className={styles.panelTitle}>
            <span className={styles.panelDot} style={{ background: 'var(--red)' }} />
            Needs Work
          </h2>
          {(weak_areas || []).length === 0
            ? <p className={styles.panelEmpty}>No weak areas identified yet</p>
            : (weak_areas || []).map(s => (
                <SubtopicRow key={s.subtopic_id}
                  name={s.name} score={s.best_score} variant="weak" />
              ))
          }
        </section>
      </div>

    </div>
  );
}
