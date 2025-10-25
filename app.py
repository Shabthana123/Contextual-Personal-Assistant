import streamlit as st
from src.db_manager import DBManager
from src.ingestion_agent_lc import LangChainIngestionAgent

st.set_page_config(page_title="Contextual Personal Assistant")
st.title("🧠 Contextual Personal Assistant")

# --- Persist agent and db across reruns ---
if "db" not in st.session_state:
    st.session_state.db = DBManager()

if "agent" not in st.session_state:
    st.session_state.agent = LangChainIngestionAgent()
    
db = st.session_state.db
agent = st.session_state.agent
thinking_agent = st.session_state.thinking_agent

st.markdown("## Add a new note")
note = st.text_area(
    "Enter note (e.g., 'Call Sarah about the Q3 budget next Monday')",
    height=120
)

if st.button("Process Note"):
    if not note.strip():
        st.warning("Please enter some note text.")
    else:
        card = agent.process_note(note.strip())
        db.conn.commit()  # ensure it's written immediately
        st.success("Note processed and stored as a new Card.")
        st.json(card)

st.markdown("---")
st.markdown("## Envelopes")
envelopes = db.get_all_envelopes()
if not envelopes:
    st.info("No envelopes found yet. Add notes to create envelopes automatically.")
else:
    for env in envelopes:
        st.write(f"**{env['name']}** (id={env['id']})")
        cards = db.get_cards_by_envelope(env['id'])
        for c in cards:
            st.write(f"- [{c['card_type']}] {c['description']}")
            if c.get('date_parsed'):
                st.caption(f"date_parsed: {c['date_parsed']}  •  assignee: {c['assignee']}")
