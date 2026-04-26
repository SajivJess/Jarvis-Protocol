import React, { useState, useEffect } from 'react';
import CodeViewport from './CodeViewport';

export default function SubstratePanel({ observation, diffData, showCacheCleared, isHealthy = true }) {
  const [displayCode, setDisplayCode] = useState(null);
  const [showDiff, setShowDiff] = useState(false);

  useEffect(() => {
    if (observation?.vulnerable_code) {
      setDisplayCode(observation.vulnerable_code);
    }
  }, [observation]);

  useEffect(() => {
    if (diffData) {
      setShowDiff(true);
      const timer = setTimeout(() => {
        setDisplayCode(diffData.newCode || diffData.newLines?.join('\n'));
        setShowDiff(false);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [diffData]);

  return (
    <div className="glass-panel p-4 flex flex-col gap-3">
      {/* Greebles */}
      <div className="greeble greeble-tl greeble-neutral" />
      <div className="greeble greeble-tr greeble-neutral" />
      <div className="greeble greeble-bl greeble-neutral" />
      <div className="greeble greeble-br greeble-neutral" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-gray-300 text-sm font-bold tracking-widest">
          SUBSTRATE // EXPRESS.JS
        </h2>
        <div className="flex items-center gap-2">
          {/* Traffic Pulse Dots */}
          <div className="flex gap-1">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-cyber-green/60"
                style={{
                  animation: `traffic-dot 1.5s ease-in-out ${i * 0.3}s infinite`,
                }}
              />
            ))}
          </div>
          {/* Health Ping */}
          <div
            className={`w-2 h-2 rounded-full ${
              isHealthy
                ? 'bg-cyber-green animate-heartbeat'
                : 'bg-gray-600'
            }`}
          />
        </div>
      </div>

      {/* Route Path */}
      {observation?.route_path && (
        <div className="text-[10px] text-gray-500" style={{ fontFamily: 'var(--font-mono)' }}>
          TARGET: {observation.route_path}
        </div>
      )}

      {/* Code Viewport */}
      <div className={`flex-1 ${showDiff ? 'ring-1 ring-cyber-amber/40' : ''}`}>
        <CodeViewport code={displayCode} />
      </div>

      {/* Cache Cleared Message */}
      {showCacheCleared && (
        <div className="text-cyber-green text-xs text-center py-1 bg-green-900/20 rounded" style={{ fontFamily: 'var(--font-mono)' }}>
          ✓ NODE_MODULE CACHE CLEARED
        </div>
      )}
    </div>
  );
}
