import React, { useState, useEffect } from 'react';

export default function TelemetryHeader({ defconStatus, mode, connectionLost }) {
  const [grpoHex, setGrpoHex] = useState('0x00000000');
  const [latency, setLatency] = useState('12.0ms');

  useEffect(() => {
    const id = setInterval(() => {
      const hex = Math.floor(Math.random() * 0xFFFFFFFF).toString(16).padStart(8, '0').toUpperCase();
      setGrpoHex(`0x${hex}`);
    }, 200);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      const ms = (8 + Math.random() * 17).toFixed(1);
      setLatency(`${ms}ms`);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-4 sm:px-6 py-2 bg-titanium-light border-b border-panel-border"
      style={{ fontFamily: 'var(--font-mono)' }}>
      <div className="flex items-center gap-3 sm:gap-6">
        <div className="text-[9px] sm:text-xs text-gray-400">
          GRPO <span className="text-cyber-cyan">{grpoHex}</span>
        </div>
        <div className="text-[9px] sm:text-xs text-gray-400">
          LATENCY <span className="text-cyber-green">{latency}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        {connectionLost && (
          <span className="text-xs px-2 py-1 bg-red-900/50 text-cyber-red rounded animate-pulse">
            CONNECTION LOST
          </span>
        )}
        {mode === 'simulation' && (
          <span className="text-xs px-2 py-1 bg-amber-900/30 text-cyber-amber rounded">
            SIMULATION MODE
          </span>
        )}
        <span
          className={`text-xs px-3 py-1 rounded font-bold ${
            defconStatus === 'breached'
              ? 'bg-cyber-red/20 text-cyber-red animate-pulse-red'
              : 'bg-green-900/30 text-cyber-green'
          }`}
        >
          DEFCON: {defconStatus === 'breached' ? 'BREACHED' : 'SECURE'}
        </span>
      </div>
    </header>
  );
}
