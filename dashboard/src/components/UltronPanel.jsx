import React, { useRef, useEffect } from 'react';

export default function UltronPanel({ attackLog, blockedStatus, currentPhase, exploitPayload, flashActive, leakedSecret }) {
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [attackLog]);

  return (
    <div className={`glass-panel p-4 flex flex-col gap-3 ${flashActive ? 'animate-flash-red' : ''}`}>
      {/* Greebles */}
      <div className="greeble greeble-tl greeble-red" />
      <div className="greeble greeble-tr greeble-red" />
      <div className="greeble greeble-bl greeble-red" />
      <div className="greeble greeble-br greeble-red" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-cyber-red text-sm font-bold tracking-widest">
          ULTRON // ATTACK VECTOR
        </h2>
        <span className="text-[10px] text-gray-500 bg-gray-800/50 px-2 py-0.5 rounded" style={{ fontFamily: 'var(--font-mono)' }}>
          PID:{Math.floor(Math.random() * 9000 + 1000)}
        </span>
      </div>

      {/* Log Area */}
      <div ref={logRef} className="log-area flex-1 p-2 bg-black/30 rounded">
        {attackLog.length === 0 && (
          <div className="text-gray-600 text-xs">Awaiting attack vector...</div>
        )}
        {attackLog.map((line, i) => (
          <div key={i} className="text-cyber-red/80">{line}</div>
        ))}
      </div>

      {/* Exploit Payload */}
      {exploitPayload && (
        <div className="p-2 bg-cyber-red/20 border border-cyber-red/40 rounded">
          <div className="text-[10px] text-gray-400 mb-1">EXPLOIT PAYLOAD</div>
          <pre className="text-white text-xs bg-cyber-red/30 p-2 rounded" style={{ fontFamily: 'var(--font-mono)' }}>
            {JSON.stringify(exploitPayload, null, 2)}
          </pre>
        </div>
      )}

      {/* Leaked Secret */}
      {leakedSecret && (
        <div className="p-2 bg-red-900/30 border border-cyber-red/30 rounded">
          <div className="text-[10px] text-gray-400 mb-1">EXFILTRATED DATA</div>
          <div className="text-cyber-red font-bold text-sm" style={{ fontFamily: 'var(--font-mono)' }}>
            secret: {leakedSecret}
          </div>
        </div>
      )}

      {/* Attack Result — phase-aware */}
      {(blockedStatus || currentPhase >= 1) && currentPhase !== 0 && (
        <div className="p-2 bg-gray-800/50 border border-gray-600/30 rounded">
          <div className="text-[10px] text-gray-400 mb-1">ATTACK RESULT</div>
          {currentPhase >= 4 && blockedStatus ? (
            <div className="text-gray-500 line-through text-sm" style={{ fontFamily: 'var(--font-mono)' }}>
              {blockedStatus}
            </div>
          ) : currentPhase >= 1 && leakedSecret ? (
            <div className="text-cyber-red text-sm font-bold" style={{ fontFamily: 'var(--font-mono)' }}>
              [200 OK] DB AUTH BYPASSED
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
