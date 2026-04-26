import { useState, useCallback } from 'react';

export function useArenaApi(baseUrl = 'http://localhost:7860') {
  const [isLive, setIsLive] = useState(false);
  const [connectionLost, setConnectionLost] = useState(false);

  const _fetch = useCallback(async (path, options = {}) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const res = await fetch(`${baseUrl}${path}`, {
        ...options,
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json', ...options.headers },
      });
      clearTimeout(timeout);
      if (!res.ok) {
        setConnectionLost(true);
        return null;
      }
      const data = await res.json();
      setConnectionLost(false);
      return data;
    } catch {
      clearTimeout(timeout);
      setConnectionLost(true);
      return null;
    }
  }, [baseUrl]);

  const healthCheck = useCallback(async () => {
    const data = await _fetch('/health');
    const live = data?.status === 'ok';
    setIsLive(live);
    if (live) setConnectionLost(false);
    return live;
  }, [_fetch]);

  const reset = useCallback(async () => {
    return await _fetch('/reset', { method: 'POST' });
  }, [_fetch]);

  const step = useCallback(async (agentOutput) => {
    return await _fetch('/step', {
      method: 'POST',
      body: JSON.stringify({ agent_output: agentOutput }),
    });
  }, [_fetch]);

  const getState = useCallback(async () => {
    return await _fetch('/state');
  }, [_fetch]);

  return { isLive, connectionLost, healthCheck, reset, step, getState };
}
