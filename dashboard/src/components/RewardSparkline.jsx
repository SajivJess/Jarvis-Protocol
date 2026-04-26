import React, { useRef, useEffect } from 'react';

export function mapValueToY(value, canvasHeight) {
  // -1.0 → bottom (canvasHeight), +1.0 → top (0), 0.0 → middle
  return canvasHeight * (1 - (value + 1) / 2);
}

export function getSegmentColor(value) {
  if (value <= -0.5) return '#FF1744';
  if (value >= 0.5) return '#00F0FF';
  return '#888888';
}

export function windowData(data, maxSize = 20) {
  if (!data || data.length === 0) return [];
  if (data.length <= maxSize) return [...data];
  return data.slice(data.length - maxSize);
}

export default function RewardSparkline({ data }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      const windowed = windowData(data, 20);

      // Clear
      ctx.fillStyle = '#0a0a1a';
      ctx.fillRect(0, 0, w, h);

      // Grid lines
      ctx.strokeStyle = '#1a1a2e';
      ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = (h / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // Dashed zero-line
      ctx.strokeStyle = '#333';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, h / 2);
      ctx.lineTo(w, h / 2);
      ctx.stroke();
      ctx.setLineDash([]);

      if (windowed.length < 2) return;

      // Draw line segments
      const step = w / (Math.max(windowed.length - 1, 1));
      for (let i = 1; i < windowed.length; i++) {
        const x0 = (i - 1) * step;
        const y0 = mapValueToY(windowed[i - 1], h);
        const x1 = i * step;
        const y1 = mapValueToY(windowed[i], h);

        ctx.strokeStyle = getSegmentColor(windowed[i]);
        ctx.lineWidth = 2;
        ctx.shadowColor = getSegmentColor(windowed[i]);
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x1, y1);
        ctx.stroke();
      }

      // Reset shadow
      ctx.shadowBlur = 0;

      // Draw points
      windowed.forEach((val, i) => {
        const x = i * step;
        const y = mapValueToY(val, h);
        ctx.fillStyle = getSegmentColor(val);
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fill();
      });
    };

    animRef.current = requestAnimationFrame(draw);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [data]);

  return (
    <div>
      <div className="text-[10px] text-gray-500 tracking-wider mb-1">REWARD TRAJECTORY</div>
      <canvas
        ref={canvasRef}
        width={240}
        height={80}
        className="w-full rounded"
        style={{ minWidth: '200px', minHeight: '80px' }}
      />
    </div>
  );
}
