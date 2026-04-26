import React from 'react';
import { useTypewriter } from '../hooks/useTypewriter';
import GateTracker from './GateTracker';
import RewardTicker from './RewardTicker';
import RewardSparkline from './RewardSparkline';
import BackpropAnimation from './BackpropAnimation';

export default function JarvisPanel({
  reasoningTrace,
  patchCode,
  gateResults,
  currentReward,
  rewardHistory,
  showBackprop,
  currentPhase,
  onBackpropComplete,
}) {
  const { displayText: traceText } = useTypewriter(reasoningTrace, 15, !!reasoningTrace);
  const { displayText: patchText } = useTypewriter(patchCode, 10, !!patchCode);

  return (
    <div className="glass-panel p-4 flex flex-col h-full overflow-hidden">
      {/* Greebles */}
      <div className="greeble greeble-tl greeble-cyan" />
      <div className="greeble greeble-tr greeble-cyan" />
      <div className="greeble greeble-bl greeble-cyan" />
      <div className="greeble greeble-br greeble-cyan" />

      {/* Header — fixed at top */}
      <h2 className="text-cyber-cyan text-sm font-bold tracking-widest mb-3 border-b border-cyan-900/50 pb-2 flex-none">
        JARVIS // COGNITIVE DEFENSE
      </h2>

      {/* Scrollable content: Trace + Patch */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-0">
        {/* Cognitive Trace */}
        <div>
          <div className="text-[10px] text-gray-500 tracking-wider mb-1">COGNITIVE TRACE</div>
          <div
            className="log-area p-3 bg-black/30 rounded text-xs text-gray-300 whitespace-pre-wrap"
            style={{ fontFamily: 'var(--font-mono)', minHeight: '60px', lineHeight: '1.8' }}
          >
            {traceText || <span className="text-gray-600">Awaiting cognitive input...</span>}
          </div>
        </div>

        {/* Synthesis Block */}
        {patchCode && (
          <div>
            <div className="text-[10px] text-gray-500 tracking-wider mb-1">PATCH SYNTHESIS</div>
            <div
              className="log-area p-2 bg-black/30 rounded text-xs text-cyber-cyan/80 whitespace-pre-wrap"
              style={{ fontFamily: 'var(--font-mono)', maxHeight: '120px' }}
            >
              {patchText}
            </div>
          </div>
        )}
      </div>

      {/* Fixed at bottom: RL Reward Telemetry */}
      <div className="flex-none shrink-0 mt-3 border-t border-cyan-900/50 pt-3 flex flex-col gap-2">
        <div className="text-[10px] text-gray-500 tracking-wider">RL REWARD TELEMETRY</div>

        <GateTracker gateResults={gateResults} currentPhase={currentPhase} />

        <BackpropAnimation show={showBackprop} onComplete={onBackpropComplete} />

        <RewardTicker value={currentReward} />

        <RewardSparkline data={rewardHistory} />
      </div>
    </div>
  );
}
