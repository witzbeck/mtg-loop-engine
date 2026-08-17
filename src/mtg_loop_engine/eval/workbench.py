"""Local Streamlit adjudication workbench (M4 research instrument, not M7)."""

from __future__ import annotations

from pathlib import Path

from mtg_loop_engine.eval.schema import AdjudicationClass, AdjudicationRecord
from mtg_loop_engine.eval.store import (
    DEFAULT_DB,
    DEFAULT_JSONL,
    AdjudicationStore,
)

CLASSES = list(AdjudicationClass)


def _ensure_loaded(store: AdjudicationStore, jsonl: Path) -> None:
    if store.list_candidates():
        return
    if jsonl.exists():
        store.import_jsonl(jsonl)


def render(
    *,
    db_path: Path | None = None,
    jsonl_path: Path | None = None,
) -> None:
    import streamlit as st

    store = AdjudicationStore(db_path or DEFAULT_DB)
    jsonl = jsonl_path or DEFAULT_JSONL
    _ensure_loaded(store, jsonl)

    st.set_page_config(page_title="M4 Adjudication Workbench", layout="wide")
    st.title("M4 Adjudication Workbench")
    st.caption("Evaluation tool only. Not the M7 explorer. JSON/IR is secondary.")

    corpus = st.sidebar.selectbox(
        "Corpus",
        ["all", "gold_pool_extras", "spellbook_absent"],
        index=1,
    )
    review_filter = st.sidebar.radio(
        "Review state",
        ["unreviewed", "reviewed", "all"],
        index=0,
    )
    reviewed = {"unreviewed": False, "reviewed": True, "all": None}[review_filter]
    corpus_arg = None if corpus == "all" else corpus
    queue = store.queue(corpus=corpus_arg, reviewed=reviewed)
    total = len(store.list_candidates(corpus=corpus_arg))
    st.sidebar.write(f"Queue {len(queue)} / {total} in corpus filter")

    if "idx" not in st.session_state:
        st.session_state.idx = 0
    if queue:
        st.session_state.idx = min(st.session_state.idx, len(queue) - 1)
    else:
        st.info("No candidates in this filter. Import JSONL or run eval-gold-extras.")
        store.close()
        return

    candidate, existing = queue[st.session_state.idx]
    st.progress((st.session_state.idx + 1) / len(queue))
    st.write(
        f"Position {st.session_state.idx + 1} of {len(queue)} · `{candidate.candidate_id}`"
    )

    left, right = st.columns(2)
    with left:
        st.subheader(candidate.left_name)
        st.text(candidate.left_oracle_text or "(no oracle text on record)")
    with right:
        st.subheader(candidate.right_name)
        st.text(candidate.right_oracle_text or "(no oracle text on record)")

    st.markdown(f"**Reference:** `{candidate.reference_status.value}`")
    st.markdown(f"**Join reasons:** {', '.join(candidate.join_reasons) or '(none)'}")
    st.markdown(
        f"**Verifier:** `{candidate.proof.status.value}` · coverage "
        f"`{candidate.proof.semantic_coverage.value}` · hash `{candidate.proof.proof_hash}`"
    )
    analysis = candidate.analysis
    st.markdown(
        f"**Essential-piece analysis:** participants={analysis.essential_functional_count} "
        f"strict_two_card={analysis.strict_two_card}"
    )
    st.markdown("**Initial-state assumptions**")
    for assumption in analysis.assumptions:
        st.write(f"- `{assumption.kind.value}` — {assumption.description}")
    st.markdown("**Prerequisites**")
    st.write("Generic:", analysis.generic_prerequisites or "(none)")
    st.write("Functional external:", analysis.functional_external_requirements or "(none)")

    st.markdown("**Setup actions**")
    setup = candidate.witness.setup_actions
    st.write("(none)" if not setup else [s.model_dump() for s in setup])
    st.markdown("**Loop body**")
    for i, step in enumerate(candidate.witness.loop_actions, start=1):
        st.write(f"{i}. `{step.op}` actor={step.actor} ability={step.ability_id} target={step.target}")

    st.markdown("**LoopRelevantState (before/after comparison from proof)**")
    for detail in candidate.proof.recurrence.details:
        st.write(f"- {detail}")
    st.markdown("**Outputs**")
    for out in candidate.proof.output_deltas:
        st.write(f"- {out.type.value}: +{out.delta_per_iteration} ({out.consequence.value})")

    st.markdown("**Why the engine accepted this**")
    st.text(candidate.explanation)

    with st.expander("Compiled IR (debug)"):
        for card in candidate.witness.card_semantics:
            st.json(card.model_dump(mode="json"))
    with st.expander("Raw witness / proof JSON (debug)"):
        st.json(candidate.witness.model_dump(mode="json"))
        st.json(candidate.proof.model_dump(mode="json"))

    default_class = (
        existing.adjudication.value if existing else AdjudicationClass.NEEDS_RULES_RESEARCH.value
    )
    choice = st.selectbox(
        "Adjudication",
        [c.value for c in CLASSES],
        index=[c.value for c in CLASSES].index(default_class),
    )
    notes = st.text_area("Reviewer notes", value=existing.notes if existing else "")

    cols = st.columns(4)
    save = cols[0].button("Save & Next", type="primary")
    back = cols[1].button("Back")
    skip = cols[2].button("Skip")
    stay = cols[3].button("Save")

    def _save(*, skipped: bool) -> None:
        store.save_adjudication(
            AdjudicationRecord(
                candidate_id=candidate.candidate_id,
                adjudication=AdjudicationClass(choice),
                notes=notes,
                proof_hash=candidate.proof.proof_hash,
                engine_version=candidate.engine_version,
                oracle_snapshot_hash=candidate.oracle_snapshot_hash,
                skipped=skipped,
            )
        )
        store.export_jsonl(jsonl)

    if save or stay:
        _save(skipped=False)
        if save and review_filter != "unreviewed":
            st.session_state.idx = min(st.session_state.idx + 1, max(len(queue) - 1, 0))
        st.rerun()
    if skip:
        _save(skipped=True)
        if review_filter != "unreviewed":
            st.session_state.idx = min(st.session_state.idx + 1, max(len(queue) - 1, 0))
        st.rerun()
    if back:
        st.session_state.idx = max(st.session_state.idx - 1, 0)
        st.rerun()
    store.close()


if __name__ == "__main__":
    render()
