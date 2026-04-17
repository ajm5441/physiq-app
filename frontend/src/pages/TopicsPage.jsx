// src/pages/TopicsPage.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTopics, useSubtopics } from '../hooks/index';
import { Card, Badge, StatusDot, ProgressBar, Button, Loader, EmptyState } from '../components/UI';
import styles from './TopicsPage.module.css';

// ── Subtopic list for one topic ───────────────────────────────────────────────
function SubtopicList({ topicId }) {
  const { subtopics, loading } = useSubtopics(topicId);
  const navigate               = useNavigate();

  if (loading) return <Loader size="sm" label="Loading subtopics…" />;

  return (
    <div className={styles.subtopicList}>
      {subtopics.map(s => {
        const canStart = s.status === 'unlocked' || s.status === 'passed' || s.status === 'skipped';
        return (
          <div key={s.subtopic_id} className={`${styles.subtopicItem} ${s.status === 'locked' ? styles.subtopicLocked : ''}`}>
            <div className={styles.subtopicLeft}>
              <StatusDot status={s.status} />
              <div>
                <div className={styles.subtopicName}>
                  {s.name}
                  {s.is_bonus && <span className={styles.bonusPill}>BONUS</span>}
                </div>
                <div className={styles.subtopicMeta}>
                  {s.status === 'locked'   && 'Locked'}
                  {s.status === 'unlocked' && 'Ready to attempt'}
                  {s.status === 'passed'   && `Best score: ${s.best_score} · ${s.attempts} attempt${s.attempts !== 1 ? 's' : ''}`}
                  {s.status === 'skipped'  && 'Skipped via Tier IV — eligible for review'}
                </div>
              </div>
            </div>
            <div className={styles.subtopicRight}>
              {s.status === 'passed' && (
                <span className={styles.subtopicScore}>{s.best_score}</span>
              )}
              {canStart && (
                <Button
                  size="sm"
                  variant={s.status === 'unlocked' ? 'primary' : 'secondary'}
                  onClick={() => navigate(`/session/${s.subtopic_id}`)}
                >
                  {s.status === 'passed' || s.status === 'skipped' ? 'Retry' : 'Start'}
                </Button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Topic accordion row ───────────────────────────────────────────────────────
function TopicRow({ topic }) {
  const [open, setOpen] = useState(topic.status !== 'locked');

  return (
    <Card className={`${styles.topicRow} ${topic.status === 'locked' ? styles.topicRowLocked : ''}`}>
      <button
        className={styles.topicToggle}
        onClick={() => setOpen(o => !o)}
        disabled={topic.status === 'locked'}
      >
        <div className={styles.topicToggleLeft}>
          <span className={styles.topicCaret}>{open ? '▾' : '▸'}</span>
          <div>
            <div className={styles.topicName}>{topic.name}</div>
            <div className={styles.topicMeta}>
              {topic.status === 'locked'
                ? 'Complete previous topic to unlock'
                : `${topic.subtopics_passed} / ${topic.subtopics_total} subtopics passed`}
            </div>
          </div>
        </div>
        <div className={styles.topicToggleRight}>
          {topic.status === 'completed' && <Badge variant="green">Complete</Badge>}
          {topic.status === 'locked'    && <Badge variant="default">Locked</Badge>}
          {topic.status === 'unlocked'  && <Badge variant="amber">In Progress</Badge>}
          {topic.bonus_unlocked && (
            <Badge variant={topic.bonus_completed ? 'teal' : 'amber'}>
              {topic.bonus_completed ? 'Bonus done' : 'Bonus ready'}
            </Badge>
          )}
          {topic.status !== 'locked' && (
            <div className={styles.topicScorePill}>
              <span className={styles.topicScoreVal}>{topic.total_score.toLocaleString()}</span>
              <span className={styles.topicScoreLbl}>pts</span>
            </div>
          )}
        </div>
      </button>

      {open && topic.status !== 'locked' && (
        <div className={styles.subtopicPanel}>
          <ProgressBar
            value={topic.subtopics_passed}
            max={topic.subtopics_total || 1}
            variant="amber"
            label={`Topic progress`}
          />
          {topic.bonus_score_threshold && (
            <div className={styles.bonusThreshold}>
              <span className={styles.bonusLabel}>Bonus unlock threshold</span>
              <span className={styles.bonusVal}>
                {topic.total_score} / {topic.bonus_score_threshold} pts
                {topic.bonus_unlocked ? ' ✓' : ''}
              </span>
            </div>
          )}
          <SubtopicList topicId={topic.topic_id} />
        </div>
      )}
    </Card>
  );
}

// ── Topics page ───────────────────────────────────────────────────────────────
export function TopicsPage() {
  const { topics, loading, error } = useTopics();

  if (loading) return <Loader size="lg" label="Loading curriculum…" />;
  if (error)   return <EmptyState icon="⚠" title="Failed to load topics" body={error} />;

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Curriculum</h1>
        <p className={styles.pageSubtitle}>Physics I · 7 main topics</p>
      </div>

      <div className={styles.topicList}>
        {topics.map(t => <TopicRow key={t.topic_id} topic={t} />)}
      </div>
    </div>
  );
}
