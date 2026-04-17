// src/context/SessionContext.jsx
import { createContext, useContext, useState, useCallback } from 'react';
import { sessionsAPI } from '../api/client';

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [sessionId,          setSessionId]          = useState(null);
  const [currentQuestion,    setCurrentQuestion]    = useState(null);
  const [questionsRemaining, setQuestionsRemaining] = useState(12);
  const [currentTier,        setCurrentTier]        = useState(1);
  const [hintPending,        setHintPending]        = useState(false);
  const [hintText,           setHintText]           = useState(null);
  const [lastResult,         setLastResult]         = useState(null); // {correct, hint_retry}
  const [sessionOutcome,     setSessionOutcome]     = useState(null); // null | 'pass' | 'fail' | 'skip_granted'
  const [loading,            setLoading]            = useState(false);
  const [error,              setError]              = useState(null);

  const startSession = useCallback(async (subtopicId) => {
    setLoading(true);
    setError(null);
    setSessionOutcome(null);
    try {
      const data = await sessionsAPI.start(subtopicId);
      setSessionId(data.session_id);
      setCurrentQuestion(data.question);
      setQuestionsRemaining(data.questions_remaining);
      setCurrentTier(data.current_tier);
      setHintPending(false);
      setHintText(null);
      setLastResult(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const submitAnswer = useCallback(async (answer) => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await sessionsAPI.answer(sessionId, answer);

      setLastResult({ correct: data.correct, hintRetry: data.hint_retry });

      if (data.session_complete) {
        setSessionOutcome(data.outcome);
        setCurrentQuestion(null);
      } else if (data.hint_retry) {
        // Wrong first attempt — show hint, hold question
        setHintPending(true);
        setHintText(data.hint);
        setQuestionsRemaining(data.questions_remaining);
        setCurrentTier(data.current_tier);
      } else {
        // Resolved — move to next question
        setHintPending(false);
        setHintText(null);
        setCurrentQuestion(data.next_question);
        setQuestionsRemaining(data.questions_remaining);
        setCurrentTier(data.current_tier);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const resetSession = useCallback(() => {
    setSessionId(null);
    setCurrentQuestion(null);
    setQuestionsRemaining(12);
    setCurrentTier(1);
    setHintPending(false);
    setHintText(null);
    setLastResult(null);
    setSessionOutcome(null);
    setError(null);
  }, []);

  return (
    <SessionContext.Provider value={{
      sessionId, currentQuestion, questionsRemaining, currentTier,
      hintPending, hintText, lastResult, sessionOutcome,
      loading, error,
      startSession, submitAnswer, resetSession,
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export const useSession = () => {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used inside SessionProvider');
  return ctx;
};
