import React, { useState, useEffect } from 'react';

const GATE_LABELS = [
  'GATE 1: FORMAT COMPLIANCE',
  'GATE 2: SYNTAX & LIVENESS',
  'GATE 3: HAPPY-PATH (REGRESSION)',
  'GATE 4: ULTRON IMMUNITY',
];

export default function GateTracker({ gateResults, currentPhase }) {
  const [visibleGates, setVisibleGates] = useState([]);

  // Reset when phase changes
  useEffect(() => {
    setVisibleGates([]);
  }, [currentPhase]);

  // Animate gates sequentially
  useEffect(() => {
    if (!gateResults || gateResults.length === 0) return;

    const timers = [];
    gateResults.forEach((gate, i) => {
      const timer = setTimeout(() => {
        setVisibleGates(prev => [...prev, gate]);
      }, (i + 1) * 300);
      timers.push(timer);
    });

    return () => timers.forEach(clearTimeout);
  }, [gateResults]);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="text-[10px] text-gray-500 tracking-wider mb-1">4-GATE WATERFALL</div>
      {GATE_LABELS.map((label, i) => {
        const gate = visibleGates.find(g => g.gate === i + 1);
        const isPassed = gate?.passed;
        const isFailed = gate && !gate.passed;

        return (
          <div key={i} className="flex items-center gap-2">
            {/* LED */}
            <div
              className={`w-2.5 h-2.5 rounded-full flex-shrink-0 transition-all duration-300 ${
                isPassed
                  ? 'bg-cyber-cyan shadow-[0_0_8px_var(--color-cyber-cyan)]'
                  : isFailed
                  ? 'bg-cyber-red animate-gate-fail shadow-[0_0_8px_var(--color-cyber-red)]'
                  : 'bg-gray-700'
              }`}
            />
            {/* Label */}
            <span className={`text-[10px] ${
              isPassed ? 'text-cyber-cyan' : isFailed ? 'text-cyber-red' : 'text-gray-600'
            }`} style={{ fontFamily: 'var(--font-mono)' }}>
              {label}
            </span>
            {/* Penalty */}
            {isFailed && (
              <span className="text-[10px] text-cyber-red ml-auto" style={{ fontFamily: 'var(--font-mono)' }}>
                [{gate.reward}] HALT
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
