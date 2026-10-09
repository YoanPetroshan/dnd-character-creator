import { useEffect, useState } from "react";

interface Props {
  value: number | undefined;
  onCommit: (value: number) => void;
  min?: number;
  max?: number;
  placeholder?: string;
}

/** Number input that keeps what the user types as a local string and only
 *  commits a valid integer on blur / Enter, so clearing the field with
 *  backspace doesn't snap back (or pass through intermediate values). */
export function CommitNumberInput({ value, onCommit, min, max, placeholder }: Props) {
  const [text, setText] = useState(value === undefined ? "" : String(value));

  useEffect(() => {
    setText(value === undefined ? "" : String(value));
  }, [value]);

  function commit() {
    const parsed = parseInt(text, 10);
    if (Number.isNaN(parsed)) {
      setText(value === undefined ? "" : String(value)); // empty/garbage: revert
      return;
    }
    const clamped = Math.min(max ?? Infinity, Math.max(min ?? -Infinity, parsed));
    setText(String(clamped));
    if (clamped !== value) onCommit(clamped);
  }

  return (
    <input
      type="number"
      inputMode="numeric"
      min={min}
      max={max}
      placeholder={placeholder}
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
      }}
    />
  );
}
