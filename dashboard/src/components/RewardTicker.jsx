import React from 'react';

export function getTickerClass(value) {
  if (value === -1.0) return 'critical-fail';
  if (value === -0.5) return 'format-fail';
  if (value === 0.0) return 'vulnerable';
  if (value === 1.0) return 'perfect-patch';
  if (value > 0.0 && value < 1.0) return 'partial-defense';
  // For values between -1.0 and -0.5 exclusive, and -0.5 to 0 exclusive
  if (value < -0.5) return 'critical-fail';
  if (value < 0.0) return 'format-fail';
  return 'vulnerable';
}

export default function RewardTicker({ value }) {
  const display = value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
  const className = getTickerClass(value);

  return (
    <div className="text-center">
      <div className="text-[10px] text-gray-500 tracking-wider mb-1">REWARD SIGNAL</div>
      <div
        className={`text-5xl font-bold ${className}`}
        style={{ fontFamily: 'var(--font-mono)', minHeight: '48px' }}
      >
        {display}
      </div>
    </div>
  );
}
