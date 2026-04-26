import React, { useEffect, useRef } from 'react';

export default function BackpropAnimation({ show, onComplete }) {
  const timerRef = useRef(null);

  useEffect(() => {
    if (show) {
      timerRef.current = setTimeout(() => {
        if (onComplete) onComplete();
      }, 1000);
    }
    return () => clearTimeout(timerRef.current);
  }, [show, onComplete]);

  if (!show) return null;

  return (
    <div className="relative w-full flex justify-center">
      <div
        className="w-[2px] h-[20px] bg-cyber-cyan animate-backprop"
        style={{ boxShadow: '0 0 15px var(--color-cyber-cyan)' }}
      />
    </div>
  );
}
