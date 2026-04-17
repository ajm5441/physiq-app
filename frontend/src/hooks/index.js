// src/hooks/index.js
import { useState, useEffect, useCallback } from 'react';
import { dashboardAPI, topicsAPI } from '../api/client';

export function useDashboard() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await dashboardAPI.get());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { data, loading, error, refetch: load };
}

export function useTopics() {
  const [topics,  setTopics]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    topicsAPI.list()
      .then(setTopics)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { topics, loading, error };
}

export function useSubtopics(topicId) {
  const [subtopics, setSubtopics] = useState([]);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);

  useEffect(() => {
    if (!topicId) return;
    setLoading(true);
    topicsAPI.subtopics(topicId)
      .then(setSubtopics)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [topicId]);

  return { subtopics, loading, error };
}
