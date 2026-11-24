import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";

/** The hero's own description (alignment, faith, looks, personality, notes): four closed sections. They describe the person,
 *  not the background, so they live on the Hero step (DESIGN-L, decision 3A; they were on the Background page). */
export function HeroDetailsForm() {
  const t = useT();
  const bp = t.backgroundPage;
  const d = t.sheet.details;
  const { draft, dispatch } = useDraft();
  return (
    <>
      <details className="details-section">
        <summary>{d.title}</summary>
        <label>
          {d.fields.alignment}
          <select value={draft.details.alignment ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "alignment", value: e.target.value })}>
            <option value="">{t.common.none}</option>
            <option value="Lawful Good">{bp.alignments["Lawful Good"]}</option>
            <option value="Neutral Good">{bp.alignments["Neutral Good"]}</option>
            <option value="Chaotic Good">{bp.alignments["Chaotic Good"]}</option>
            <option value="Lawful Neutral">{bp.alignments["Lawful Neutral"]}</option>
            <option value="True Neutral">{bp.alignments["True Neutral"]}</option>
            <option value="Chaotic Neutral">{bp.alignments["Chaotic Neutral"]}</option>
            <option value="Lawful Evil">{bp.alignments["Lawful Evil"]}</option>
            <option value="Neutral Evil">{bp.alignments["Neutral Evil"]}</option>
            <option value="Chaotic Evil">{bp.alignments["Chaotic Evil"]}</option>
          </select>
        </label>
        <label>
          {d.fields.faith}
          <input type="text" value={draft.details.faith ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "faith", value: e.target.value })} />
        </label>
        <label>
          {d.fields.lifestyle}
          <input type="text" value={draft.details.lifestyle ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "lifestyle", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>{d.sections.physical}</summary>
        <label>
          {d.fields.age}
          <input type="text" value={draft.details.age ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "age", value: e.target.value })} />
        </label>
        <label>
          {d.fields.height}
          <input type="text" value={draft.details.height ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "height", value: e.target.value })} />
        </label>
        <label>
          {d.fields.weight}
          <input type="text" value={draft.details.weight ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "weight", value: e.target.value })} />
        </label>
        <label>
          {d.fields.eyes}
          <input type="text" value={draft.details.eyes ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "eyes", value: e.target.value })} />
        </label>
        <label>
          {d.fields.skin}
          <input type="text" value={draft.details.skin ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "skin", value: e.target.value })} />
        </label>
        <label>
          {d.fields.hair}
          <input type="text" value={draft.details.hair ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "hair", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>{d.sections.personality}</summary>
        <label>
          {d.fields.personalityTraits}
          <textarea value={draft.details.personalityTraits ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "personalityTraits", value: e.target.value })} />
        </label>
        <label>
          {d.fields.ideals}
          <textarea value={draft.details.ideals ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "ideals", value: e.target.value })} />
        </label>
        <label>
          {d.fields.bonds}
          <textarea value={draft.details.bonds ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "bonds", value: e.target.value })} />
        </label>
        <label>
          {d.fields.flaws}
          <textarea value={draft.details.flaws ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "flaws", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>{d.sections.notes}</summary>
        <label>
          {d.fields.backstory}
          <textarea value={draft.details.backstory ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "backstory", value: e.target.value })} />
        </label>
        <label>
          {d.fields.organizations}
          <textarea value={draft.details.organizations ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "organizations", value: e.target.value })} />
        </label>
        <label>
          {d.fields.allies}
          <textarea value={draft.details.allies ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "allies", value: e.target.value })} />
        </label>
        <label>
          {d.fields.enemies}
          <textarea value={draft.details.enemies ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "enemies", value: e.target.value })} />
        </label>
        <label>
          {d.fields.notes}
          <textarea value={draft.details.notes ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "notes", value: e.target.value })} />
        </label>
      </details>
    </>
  );
}
