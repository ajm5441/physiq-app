// src/pages/SessionPage.jsx
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { TierIndicator, QuestionCounter, Button, Badge, Loader } from '../components/UI';
import styles from './SessionPage.module.css';

// ── Question display ──────────────────────────────────────────────────────────
function QuestionCard({ question, onSubmit, loading, lastResult, hintPending, hintText }) {
  const [answer,    setAnswer]    = useState('');
  const [selected,  setSelected]  = useState(null);   // for multiple choice
  const [showHint,  setShowHint]  = useState(false);

  // Reset input state when question changes
  useEffect(() => {
    setAnswer('');
    setSelected(null);
    setShowHint(false);
  }, [question?.question_id]);

  // Auto-show hint when hint_pending fires
  useEffect(() => {
    if (hintPending && hintText) setShowHint(true);
  }, [hintPending, hintText]);

  const handleSubmit = () => {
    const val = question.type === 'multiple_choice' ? selected : answer.trim();
    if (!val) return;
    onSubmit(val);
    // Don't clear — keep the answer visible while result is shown
  };

  const isReview = question.is_review;

  return (
    <div className={`${styles.questionCard} ${isReview ? styles.questionReview : ''}`}>
      {/* Review indicator */}
      {isReview && (
        <div className={styles.reviewBanner}>
          <span className={styles.reviewIcon}>↩</span>
          Review question
        </div>
      )}

      {/* Tier badge */}
      <div className={styles.questionMeta}>
        <Badge variant="amber">Tier {question.tier}</Badge>
        {hintPending && <Badge variant="default">Hint active</Badge>}
      </div>

      {/* Prompt */}
      <div className={styles.questionPrompt}>{question.prompt}</div>

      {/* Hint reveal */}
      {showHint && hintText && (
        <div className={styles.hintBox}>
          <span className={styles.hintLabel}>Hint</span>
          <p className={styles.hintText}>{hintText}</p>
        </div>
      )}

      {/* Result feedback */}
      {lastResult && !hintPending && (
        <div className={`${styles.resultBanner} ${lastResult.correct ? styles.resultCorrect : styles.resultWrong}`}>
          {lastResult.correct ? '✓ Correct' : '✗ Incorrect'}
          {lastResult.hintRetry && !lastResult.correct && ' — question exhausted'}
        </div>
      )}

      {/* Answer input */}
      <div className={styles.answerSection}>
        {question.type === 'multiple_choice' && question.options ? (
          <div className={styles.optionGrid}>
            {question.options.map(opt => (
              <button
                key={opt.key}
                className={`${styles.optionBtn} ${selected === opt.key ? styles.optionSelected : ''}`}
                onClick={() => setSelected(opt.key)}
                disabled={loading}
              >
                <span className={styles.optionKey}>{opt.key}</span>
                <span className={styles.optionText}>{opt.text}</span>
              </button>
            ))}
          </div>
        ) : question.type === 'numeric' ? (
          <div className={styles.numericWrap}>
            <input
              type="text"
              inputMode="decimal"
              className={styles.numericInput}
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="Enter numeric answer…"
              disabled={loading}
              autoFocus
            />
            <span className={styles.numericHint}>Units not required</span>
          </div>
        ) : (
          <textarea
            className={styles.freeInput}
            value={answer}
            onChange={e => setAnswer(e.target.value)}
            placeholder="Enter your response…"
            rows={3}
            disabled={loading}
          />
        )}

        <Button
          onClick={handleSubmit}
          loading={loading}
          disabled={question.type === 'multiple_choice' ? !selected : !answer.trim()}
          size="lg"
          className={styles.submitBtn}
        >
          {hintPending ? 'Submit (hint retry)' : 'Submit Answer'}
        </Button>
      </div>
    </div>
  );
}

// ── Outcome screen ────────────────────────────────────────────────────────────
function OutcomeScreen({ outcome, subtopicName, onContinue, onRetry }) {
  const config = {
    pass: {
      icon: '◈', color: 'var(--green)',
      title: 'Subtopic Passed',
      body: `You've passed ${subtopicName}. The next subtopic is now unlocked.`,
    },
    skip_granted: {
      icon: '◆', color: 'var(--amber)',
      title: 'Skip Granted!',
      body: `Outstanding performance on ${subtopicName}. You've skipped the next subtopic and unlocked the one after it.`,
    },
    fail: {
      icon: '◇', color: 'var(--red)',
      title: 'Session Failed',
      body: `You didn't reach Tier III on ${subtopicName} this time. Review the hints and try again.`,
    },
  }[outcome] || { icon: '○', color: 'var(--text-muted)', title: 'Session Complete', body: '' };

  return (
    <div className={styles.outcome}>
      <div className={styles.outcomeIcon} style={{ color: config.color }}>
        {config.icon}
      </div>
      <h2 className={styles.outcomeTitle} style={{ color: config.color }}>
        {config.title}
      </h2>
      <p className={styles.outcomeBody}>{config.body}</p>
      <div className={styles.outcomeActions}>
        {outcome !== 'fail'
          ? <Button size="lg" onClick={onContinue}>Back to Topics</Button>
          : <>
              <Button size="lg" onClick={onRetry}>Try Again</Button>
              <Button size="lg" variant="ghost" onClick={onContinue}>Back to Topics</Button>
            </>
        }
      </div>
    </div>
  );
}

// ── Session page ──────────────────────────────────────────────────────────────
export function SessionPage() {
  const { subtopicId }  = useParams();
  const navigate        = useNavigate();
  const {
    sessionId, currentQuestion, questionsRemaining, currentTier,
    hintPending, hintText, lastResult, sessionOutcome,
    loading, error,
    startSession, submitAnswer, resetSession,
  } = useSession();

  // Derive tier_correct from session state if available
  // (the relay returns it on each /answer response but we track it in context)
  const [tierCorrect, setTierCorrect] = useState({ 1: 0, 2: 0, 3: 0, 4: 0 });
  const [subtopicName, setSubtopicName] = useState('');

  useEffect(() => {
    if (subtopicId) {
      resetSession();
      startSession(parseInt(subtopicId, 10));
    }
  }, [subtopicId]);

  // Update tier correct counts when lastResult changes
  useEffect(() => {
    if (lastResult?.correct && currentTier) {
      setTierCorrect(prev => ({
        ...prev,
        // Credit goes to the tier the current question was from
        // We can approximate from currentTier before it advanced
        [currentTier]: Math.min((prev[currentTier] || 0) + 1, 2),
      }));
    }
  }, [lastResult]);

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.errorBox}>
          <p className={styles.errorText}>{error}</p>
          <Button variant="ghost" onClick={() => navigate('/topics')}>
            Back to Topics
          </Button>
        </div>
      </div>
    );
  }

  if (!sessionId && loading) {
    return (
      <div className={styles.page}>
        <Loader size="lg" label="Initializing session…" />
      </div>
    );
  }

  if (sessionOutcome) {
    return (
      <div className={styles.page}>
        <OutcomeScreen
          outcome={sessionOutcome}
          subtopicName={subtopicName || 'this subtopic'}
          onContinue={() => { resetSession(); navigate('/topics'); }}
          onRetry={() => { resetSession(); startSession(parseInt(subtopicId, 10)); }}
        />
      </div>
    );
  }

  return (
    <div className={styles.page}>

      {/* ── Session HUD ──────────────────────────────────────────────────── */}
      <div className={styles.hud}>
        <TierIndicator currentTier={currentTier} tierCorrect={tierCorrect} />
        <div className={styles.hudCenter}>
          <span className={styles.hudLabel}>SESSION</span>
          <span className={styles.hudSessionId}>
            #{String(sessionId || 0).padStart(5, '0')}
          </span>
        </div>
        <QuestionCounter used={12 - (questionsRemaining ?? 12)} total={12} />
      </div>

      {/* ── Progress track ───────────────────────────────────────────────── */}
      <div className={styles.progressTrack}>
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className={`${styles.progressPip} ${
              i < (12 - (questionsRemaining ?? 12)) ? styles.progressPipUsed : ''
            }`}
          />
        ))}
      </div>

      {/* ── Question ─────────────────────────────────────────────────────── */}
      {currentQuestion ? (
        <QuestionCard
          question={currentQuestion}
          onSubmit={submitAnswer}
          loading={loading}
          lastResult={lastResult}
          hintPending={hintPending}
          hintText={hintText}
        />
      ) : (
        <Loader size="md" label="Loading question…" />
      )}
    </div>
  );
}
