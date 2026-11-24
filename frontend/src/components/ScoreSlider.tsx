import { useEffect, useRef, useState } from "react";

interface Props {
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
  ariaLabel: string;
}

/** Minimum gap between two updates of the draft while the thumb is dragged (the page re-resolves after the last one). */
export const SLIDER_THROTTLE_MS = 80;

/** A range input that follows the thumb at once and passes the value on at most every SLIDER_THROTTLE_MS (the last
 *  value is always passed). The typed number field next to it stays the exact input. */
export function ScoreSlider({ value, min, max, onChange, ariaLabel }: Props) {
  const [live, setLive] = useState(value);
  const timer = useRef<number | undefined>(undefined);
  const lastSent = useRef(0);

  // follow the draft, unless a newer value of the thumb has not been passed on yet
  useEffect(() => {
    if (timer.current === undefined) setLive(value);
  }, [value]);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  function push(next: number) {
    setLive(next);
    window.clearTimeout(timer.current);
    const wait = Math.max(0, SLIDER_THROTTLE_MS - (Date.now() - lastSent.current));
    const send = () => {
      timer.current = undefined;
      lastSent.current = Date.now();
      onChange(next);
    };
    if (wait === 0) send();
    else timer.current = window.setTimeout(send, wait);
  }

  return (
    <input
      type="range"
      className="score-slider"
      min={min}
      max={max}
      step={1}
      aria-label={ariaLabel}
      value={Math.min(max, Math.max(min, live))}
      onChange={(e) => push(Number(e.target.value))}
    />
  );
}
