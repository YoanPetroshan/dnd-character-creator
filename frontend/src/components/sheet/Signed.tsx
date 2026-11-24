/** A signed number as the online sheet shows it: the sign smaller and lighter than the digits ("+3"). */
export function Signed({ value }: { value: string }) {
  const m = /^([+\u2212-])(.*)$/.exec(value);
  if (!m) return <>{value}</>;
  return (
    <>
      <span className="signed__sign">{m[1]}</span>
      {m[2]}
    </>
  );
}
