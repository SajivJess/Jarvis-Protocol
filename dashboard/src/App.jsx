import React, { useState, useEffect, useCallback } from 'react';
import TelemetryHeader from './components/TelemetryHeader';
import UltronPanel from './components/UltronPanel';
import SubstratePanel from './components/SubstratePanel';
import JarvisPanel from './components/JarvisPanel';
import { useArenaApi } from './hooks/useArenaApi';
import { simulationData } from './lib/simulationData';

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const NEGATIVE_SEED = [-1.0, -0.5, -0.3, -1.0, -0.5, -0.8, -0.5, -1.0];

export default function App() {
  // Core state
  const [currentPhase, setCurrentPhase] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [defconStatus, setDefconStatus] = useState('secure');
  const [mode, setMode] = useState('simulation');
  const [rewardHistory, setRewardHistory] = useState([...NEGATIVE_SEED]);
  const [gateResults, setGateResults] = useState([]);
  const [currentReward, setCurrentReward] = useState(0);
  const [observation, setObservation] = useState(null);
  const [attackLog, setAttackLog] = useState([]);
  const [blockedStatus, setBlockedStatus] = useState(null);
  const [exploitPayload, setExploitPayload] = useState(null);
  const [flashActive, setFlashActive] = useState(false);
  const [leakedSecret, setLeakedSecret] = useState(null);
  const [reasoningTrace, setReasoningTrace] = useState('');
  const [patchCode, setPatchCode] = useState('');
  const [showBackprop, setShowBackprop] = useState(false);
  const [diffData, setDiffData] = useState(null);
  const [showCacheCleared, setShowCacheCleared] = useState(false);
  const [connectionLost, setConnectionLost] = useState(false);

  const api = useArenaApi();

  // On mount: health check + mode detection
  useEffect(() => {
    const init = async () => {
      const live = await api.healthCheck();
      if (live) {
        setMode('live');
        const state = await api.getState();
        if (state) setObservation(state);
      } else {
        setMode('simulation');
        setObservation(simulationData.observation);
      }
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync connectionLost from api
  useEffect(() => {
    setConnectionLost(api.connectionLost);
  }, [api.connectionLost]);

  // Phase functions
  const phase1 = useCallback(async () => {
    setCurrentPhase(1);
    setGateResults([]);
    setBlockedStatus(null);
    setLeakedSecret(null);
    setExploitPayload(null);
    setFlashActive(false);
    setAttackLog([]);

    let obs, stepResult;

    if (mode === 'live' && api.isLive) {
      obs = await api.reset();
      if (obs) setObservation(obs);
      stepResult = await api.step(simulationData.badPatch);
    } else {
      obs = simulationData.observation;
      setObservation(obs);
      stepResult = simulationData.phase1Response;
    }

    // Animate attack log entries one by one
    for (let i = 0; i < simulationData.attackLog.length; i++) {
      await delay(400);
      setAttackLog(prev => [...prev, simulationData.attackLog[i]]);
    }

    await delay(300);
    setExploitPayload(simulationData.exploitPayload);

    // Animate gates
    if (stepResult?.info?.gates) {
      setGateResults(stepResult.info.gates);
    }

    await delay(1500);

    // Set reward
    const reward = stepResult?.reward ?? -1.0;
    setCurrentReward(reward);

    // Flash Ultron panel
    setFlashActive(true);
    await delay(500);
    setFlashActive(false);

    // DEFCON breached
    setDefconStatus('breached');

    // Show leaked secret
    setLeakedSecret(simulationData.leakedSecret);

    // Append to reward history
    setRewardHistory(prev => [...prev, reward]);
  }, [mode, api]);

  const phase2 = useCallback(async () => {
    setCurrentPhase(2);
    setReasoningTrace(simulationData.reasoningTrace);
    await delay(500);
    setPatchCode(simulationData.correctPatch);
  }, []);

  const phase3 = useCallback(async () => {
    setCurrentPhase(3);
    setGateResults([]);

    let stepResult;

    if (mode === 'live' && api.isLive) {
      stepResult = await api.step(simulationData.correctPatch);
    } else {
      stepResult = simulationData.phase3Response;
    }

    // Animate gates
    if (stepResult?.info?.gates) {
      setGateResults(stepResult.info.gates);
    }

    await delay(1500);

    // Set reward
    const reward = stepResult?.reward ?? 1.0;
    setCurrentReward(reward);

    // Trigger backprop
    setShowBackprop(true);

    // Diff data
    setDiffData({
      oldCode: simulationData.observation.vulnerable_code,
      newCode: simulationData.correctPatch,
    });

    await delay(1000);
    setShowCacheCleared(true);

    // DEFCON secure
    setDefconStatus('secure');

    // Append to reward history
    setRewardHistory(prev => [...prev, reward]);
  }, [mode, api]);

  const phase4 = useCallback(async () => {
    setCurrentPhase(4);
    setBlockedStatus('401 UNAUTHORIZED');
  }, []);

  const runPhase = useCallback(async (n) => {
    if (isTransitioning) return;
    setIsTransitioning(true);
    try {
      switch (n) {
        case 1: await phase1(); break;
        case 2: await phase2(); break;
        case 3: await phase3(); break;
        case 4: await phase4(); break;
        default: break;
      }
    } finally {
      setIsTransitioning(false);
    }
  }, [isTransitioning, phase1, phase2, phase3, phase4]);

  // Keyboard listener
  useEffect(() => {
    const handler = (e) => {
      const n = parseInt(e.key, 10);
      if (n >= 1 && n <= 4) {
        runPhase(n);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [runPhase]);

  const handleBackpropComplete = useCallback(() => {
    setShowBackprop(false);
  }, []);

  return (
    <div className="min-h-screen bg-titanium text-white overflow-hidden relative">
      {/* Scanline Overlay */}
      <div className="scanline-overlay" />

      {/* Telemetry Header */}
      <TelemetryHeader
        defconStatus={defconStatus}
        mode={mode}
        connectionLost={connectionLost}
      />

      {/* Main 3-Column Grid */}
      <main className="grid grid-cols-1 xl:grid-cols-3 gap-4 p-4 pt-16 h-[calc(100vh)] overflow-hidden">
        <UltronPanel
          attackLog={attackLog}
          blockedStatus={blockedStatus}
          currentPhase={currentPhase}
          exploitPayload={exploitPayload}
          flashActive={flashActive}
          leakedSecret={leakedSecret}
        />
        <SubstratePanel
          observation={observation}
          diffData={diffData}
          showCacheCleared={showCacheCleared}
        />
        <JarvisPanel
          reasoningTrace={reasoningTrace}
          patchCode={patchCode}
          gateResults={gateResults}
          currentReward={currentReward}
          rewardHistory={rewardHistory}
          showBackprop={showBackprop}
          currentPhase={currentPhase}
          onBackpropComplete={handleBackpropComplete}
        />
      </main>

      {/* Overlay Buttons */}
      <div className="fixed inset-0 z-30 grid grid-cols-4 pointer-events-none">
        {[1, 2, 3, 4].map(n => (
          <button
            key={n}
            onClick={() => runPhase(n)}
            className="pointer-events-auto opacity-0 hover:opacity-5 hover:bg-white/5 transition-opacity cursor-pointer"
            aria-label={`Phase ${n}`}
          />
        ))}
      </div>
    </div>
  );
}
