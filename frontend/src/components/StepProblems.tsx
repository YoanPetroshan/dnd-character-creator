import { useResolutionContext } from "../ResolutionContext";
import { problemsForStep, type ProblemStep } from "../problems";

/** Blocking problems that belong to this wizard step (also counted in the
 *  StepNav badge), so they are visible where they can be fixed. */
export function StepProblems({ step }: { step: ProblemStep }) {
  const { resolution } = useResolutionContext();
  const list = resolution ? problemsForStep(resolution.problems, step) : [];
  if (list.length === 0) return null;
  return (
    <ul className="step-problems" role="alert">
      {list.map((p) => (
        <li key={p.id}>{p.message}</li>
      ))}
    </ul>
  );
}
