import { useState, useEffect, useRef } from 'react';

export function useTypewriter(text, speed = 30, trigger = true) {
  const [displayText, setDisplayText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (!text || !trigger) {
      setDisplayText('');
      setIsComplete(false);
      return;
    }
    setDisplayText('');
    setIsComplete(false);
    let i = 0;
    const tick = () => {
      if (i < text.length) {
        setDisplayText(text.slice(0, i + 1));
        i++;
        timeoutRef.current = setTimeout(tick, speed);
      } else {
        setIsComplete(true);
      }
    };
    tick();
    return () => clearTimeout(timeoutRef.current);
  }, [text, speed, trigger]);

  return { displayText, isComplete };
}
