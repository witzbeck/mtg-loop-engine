"""Local Streamlit adjudication workbench (M4 research instrument, not M7)."""

from __future__ import annotations

from pathlib import Path

from mtg_loop_engine.eval.glossary import GLOSSARY
from mtg_loop_engine.eval.narrate import card_image_url, full_narrative, narrate_loop
from mtg_loop_engine.eval.schema import AdjudicationClass, AdjudicationRecord
from mtg_loop_engine.eval.store import (
    DEFAULT_DB,
    DEFAULT_JSONL,
    AdjudicationStore,
)

CLASSES = list(AdjudicationClass)

# ---------------------------------------------------------------------------
# Adjudication class guide: one sentence + example pair for each class
# ---------------------------------------------------------------------------

_CLASS_GUIDE: list[tuple[str, str, str]] = [
    (
        AdjudicationClass.VALID_STRICT_TWO_CARD.value,
        "Both cards actively participate in every iteration; no third functional piece is required.",
        "Basalt Monolith + Rings of Brighthearth",
    ),
    (
        AdjudicationClass.VALID_GENERIC_PREREQUISITE.value,
        "The loop needs a third object (e.g. 'any creature to sacrifice'), but that object's "
        "identity is irrelevant — any legal substitute works.",
        "Phyrexian Altar + Gravecrawler (needs any Zombie on board)",
    ),
    (
        AdjudicationClass.FUNCTIONAL_EXTERNAL_REQUIREMENT.value,
        "A specific third card type is required that isn't 'any creature/artifact' — "
        "it must have a particular ability.",
        "Deadeye Navigator + Peregrine Drake (needs a land that taps for 5+)",
    ),
    (
        AdjudicationClass.UNJUSTIFIED_INITIAL_STATE.value,
        "The starting board state the engine assumed (e.g. tokens pre-seeded) is not "
        "something the combo itself can set up in a normal game.",
        "Engine seeds 5 tokens; the pair only ever creates 1 per loop iteration.",
    ),
    (
        AdjudicationClass.RULES_OR_SEMANTICS_FALSE_POSITIVE.value,
        "The engine made a rules mistake — the loop is not actually legal (wrong timing, "
        "wrong zone, a 'once per turn' limit, etc.).",
        "Engine ignores 'activate only as a sorcery' restriction.",
    ),
    (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION.value,
        "One of the two 'essential' cards never does anything in the loop — "
        "it's a bystander, not a participant.",
        "Basalt Monolith loops by itself; the second card just watches.",
    ),
    (
        AdjudicationClass.INVALID_CANDIDATE_DATA.value,
        "One or both cards don't exist as real Magic cards — e.g. a test fixture "
        "stand-in, a missing oracle text, or a lookup failure. "
        "Excluded from precision calculations entirely.",
        "\"Impact Tremors Lite\" is a gold-core fixture, not a real card.",
    ),
    (
        AdjudicationClass.NEEDS_RULES_RESEARCH.value,
        "You're not sure — leave it here and come back after checking the rules.",
        "(use liberally; it's better than a wrong label)",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_loaded(store: AdjudicationStore, jsonl: Path) -> None:
    if store.list_candidates():
        return
    if jsonl.exists():
        store.import_jsonl(jsonl)


def _render_card_header(st, name: str, oracle_text: str) -> None:
    """Card image + oracle text side by side in a bordered container."""
    with st.container(border=True):
        img_col, text_col = st.columns([1, 2])
        with img_col:
            st.image(card_image_url(name), caption=name)
        with text_col:
            st.subheader(name)
            st.text(oracle_text or "(no oracle text on record)")
            # Inline glossary: highlight any jargon terms that appear in the text
            hits = [term for term, _ in GLOSSARY if term.split(" ")[0].lower() in oracle_text.lower()]
            if hits:
                with st.expander(":material/menu_book: Jargon in this card's text", expanded=False):
                    for term in hits[:6]:  # cap to avoid overwhelming
                        defn = dict(GLOSSARY)[term]
                        st.markdown(f"**{term}** — {defn}")


def _render_loop_narrative(st, witness, proof) -> None:
    st.markdown("#### How the loop works")
    st.markdown(full_narrative(witness, proof))


def _render_verifier_details(st, candidate) -> None:
    with st.expander(":material/verified: Verifier details", expanded=False):
        st.markdown(
            f"**Status:** `{candidate.proof.status.value}`  \n"
            f"**Coverage:** `{candidate.proof.semantic_coverage.value}`  \n"
            f"**Proof hash:** `{candidate.proof.proof_hash}`"
        )
        analysis = candidate.analysis
        st.markdown(
            f"**Essential-piece analysis:** "
            f"{analysis.essential_functional_count} participating card(s), "
            f"`strict_two_card={analysis.strict_two_card}`"
        )
        st.markdown("**Starting-state assumptions**")
        for assumption in analysis.assumptions:
            st.write(f"- `{assumption.kind.value}` — {assumption.description}")
        st.markdown("**Prerequisites**")
        st.write("Generic:", analysis.generic_prerequisites or "(none)")
        st.write("Functional external:", analysis.functional_external_requirements or "(none)")

        st.markdown("**Join reasons** (why the engine paired these cards)")
        st.write(", ".join(candidate.join_reasons) or "(none)")

        st.markdown("**LoopRelevantState (before/after comparison)**")
        for detail in candidate.proof.recurrence.details:
            st.write(f"- {detail}")

        st.markdown("**Outputs per iteration**")
        for out in candidate.proof.output_deltas:
            st.write(f"- {out.type.value}: +{out.delta_per_iteration} ({out.consequence.value})")

    with st.expander(":material/code: Compiled IR (debug)", expanded=False):
        for card in candidate.witness.card_semantics:
            st.json(card.model_dump(mode="json"))

    with st.expander(":material/data_object: Raw witness / proof JSON (debug)", expanded=False):
        st.json(candidate.witness.model_dump(mode="json"))
        st.json(candidate.proof.model_dump(mode="json"))


def _render_adjudication_controls(st, store, candidate, existing, queue, review_filter, jsonl) -> None:
    default_class = (
        existing.adjudication.value if existing else AdjudicationClass.NEEDS_RULES_RESEARCH.value
    )
    choice = st.selectbox(
        "Adjudication",
        [c.value for c in CLASSES],
        index=[c.value for c in CLASSES].index(default_class),
    )
    notes = st.text_area("Reviewer notes", value=existing.notes if existing else "")

    with st.container(horizontal=True):
        save = st.button(":material/save: Save & next", type="primary")
        back = st.button(":material/arrow_back: Back")
        skip = st.button(":material/skip_next: Skip")
        stay = st.button(":material/check: Save")

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


# ---------------------------------------------------------------------------
# Sidebar panels
# ---------------------------------------------------------------------------

def _render_sidebar_guide(st) -> None:
    with st.sidebar.expander(":material/menu_book: How to adjudicate", expanded=False):
        for cls_val, explanation, example in _CLASS_GUIDE:
            st.markdown(f"**`{cls_val}`**")
            st.caption(explanation)
            st.caption(f"Example: {example}")
            st.space("small")


def _render_sidebar_glossary(st) -> None:
    with st.sidebar.expander(":material/library_books: MTG glossary", expanded=False):
        for term, defn in GLOSSARY:
            st.markdown(f"**{term}**")
            st.caption(defn)


# ---------------------------------------------------------------------------
# Gold-core study tab
# ---------------------------------------------------------------------------

def _render_study_tab(st) -> None:
    """Browse known-good gold-core loops to calibrate your eye."""
    st.markdown(
        "These are loops the engine has verified against hand-authored rules proofs. "
        "Use them to get a feel for what a confirmed valid loop looks like."
    )
    try:
        from mtg_loop_engine.corpus import all_gold_core
        from mtg_loop_engine.verify.verifier import Verifier

        witnesses = all_gold_core()
    except Exception as exc:
        st.error(f"Could not load gold-core corpus: {exc}")
        return

    if not witnesses:
        st.info("No gold-core witnesses found.")
        return

    verifier = Verifier()
    names = [" + ".join(c.name for c in w.essential_cards) for w in witnesses]

    if "study_idx" not in st.session_state:
        st.session_state.study_idx = 0

    chosen = st.selectbox("Select a gold-core loop", names, index=st.session_state.study_idx)
    st.session_state.study_idx = names.index(chosen)
    w = witnesses[st.session_state.study_idx]

    proof = verifier.verify(w)

    # Card images + oracle text
    cards = w.essential_cards
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            with st.container(border=True):
                st.image(card_image_url(card.name), caption=card.name)
                # Find oracle text from fixtures
                try:
                    from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
                    fixture = GOLD_ORACLE_FIXTURES.get(card.oracle_id)
                    oracle_text = fixture.oracle_text if fixture else ""
                except Exception:
                    oracle_text = ""
                st.text(oracle_text or "(no oracle text on record)")

    st.space("small")
    st.markdown(full_narrative(w, proof))

    with st.expander(":material/verified: Proof details", expanded=False):
        st.markdown(f"**Status:** `{proof.status.value}` · Coverage `{proof.semantic_coverage.value}`")
        st.markdown("**Recurrence dimensions:**")
        for detail in proof.recurrence.details:
            st.write(f"- {detail}")
        st.markdown("**Outputs:**")
        for out in proof.output_deltas:
            st.write(f"- {out.type.value}: +{out.delta_per_iteration} ({out.consequence.value})")

    with st.container(horizontal=True):
        if st.button(":material/arrow_back: Previous", key="study_prev"):
            st.session_state.study_idx = max(st.session_state.study_idx - 1, 0)
            st.rerun()
        if st.button(":material/arrow_forward: Next", key="study_next"):
            st.session_state.study_idx = min(st.session_state.study_idx + 1, len(witnesses) - 1)
            st.rerun()


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render(
    *,
    db_path: Path | None = None,
    jsonl_path: Path | None = None,
) -> None:
    import streamlit as st

    store = AdjudicationStore(db_path or DEFAULT_DB)
    jsonl = jsonl_path or DEFAULT_JSONL
    _ensure_loaded(store, jsonl)

    st.set_page_config(
        page_title="MTG Loop Engine — adjudication workbench",
        page_icon=":material/loop:",
        layout="wide",
    )
    st.title(":material/loop: MTG Loop Engine — adjudication workbench")
    st.caption("M4 research instrument. Not the M7 explorer.")

    # Sidebar: filters + tutorial panels
    corpus = st.sidebar.selectbox(
        "Corpus",
        ["all", "gold_pool_extras", "spellbook_absent"],
        index=1,
    )
    review_filter = st.sidebar.segmented_control(
        "Review state",
        options=["unreviewed", "reviewed", "all"],
        default="unreviewed",
    )
    reviewed = {"unreviewed": False, "reviewed": True, "all": None}[review_filter]
    corpus_arg = None if corpus == "all" else corpus

    _render_sidebar_guide(st)
    _render_sidebar_glossary(st)

    # Top-level tabs
    review_tab, study_tab = st.tabs([
        ":material/rate_review: Review candidates",
        ":material/school: Study gold-core loops",
    ])

    # ---- Study tab (no adjudication, just learning) -------------------------
    with study_tab:
        _render_study_tab(st)

    # ---- Review tab ---------------------------------------------------------
    with review_tab:
        queue = store.queue(corpus=corpus_arg, reviewed=reviewed)
        total = len(store.list_candidates(corpus=corpus_arg))
        st.caption(f"Queue: {len(queue)} of {total} in this filter")

        if "idx" not in st.session_state:
            st.session_state.idx = 0
        if queue:
            st.session_state.idx = min(st.session_state.idx, len(queue) - 1)
        else:
            st.info(
                "No candidates in this filter. "
                "Import a JSONL file or run `eval-gold-extras` to populate.",
                icon=":material/info:",
            )
            store.close()
            return

        candidate, existing = queue[st.session_state.idx]
        st.progress((st.session_state.idx + 1) / len(queue))
        st.caption(
            f"Candidate {st.session_state.idx + 1} of {len(queue)} · "
            f"`{candidate.candidate_id}` · "
            f"reference: `{candidate.reference_status.value}`"
        )

        # Card images + oracle text
        left_col, right_col = st.columns(2)
        with left_col:
            _render_card_header(st, candidate.left_name, candidate.left_oracle_text)
        with right_col:
            _render_card_header(st, candidate.right_name, candidate.right_oracle_text)

        st.space("small")

        # Plain-English narrative
        _render_loop_narrative(st, candidate.witness, candidate.proof)

        st.space("small")

        # Collapsible technical details
        _render_verifier_details(st, candidate)

        st.space("small")

        # Adjudication controls
        st.markdown("#### Your verdict")
        _render_adjudication_controls(
            st, store, candidate, existing, queue, review_filter, jsonl
        )

    store.close()


if __name__ == "__main__":
    render()
