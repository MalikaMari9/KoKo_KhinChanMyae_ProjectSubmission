import streamlit as st
import json

# -------------------------------------
# IMPORT UTIL FUNCTIONS
# -------------------------------------
from bedrock_utils import (
    
    query_knowledge_base,
    generate_response,
    valid_prompt  
)

# -------------------------------------
# STREAMLIT APP UI
# -------------------------------------

st.title("Heavy Machinery Chat (Bedrock)")

st.sidebar.header("Configuration")

model_id = st.sidebar.selectbox(
    "Select LLM Model",
    ["amazon.titan-text-express-v1", "amazon.titan-text-lite-v1"]
)

kb_id = st.sidebar.text_input("Knowledge Base ID", "KBDYKC1GEK")

temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.7)
top_p = st.sidebar.slider("Top P", 0.0, 1.0, 0.9)

# Initialize chat memory
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display prior conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
prompt = st.chat_input("Ask about machinery!")

# DETAIL KEYWORDS for distinguishing "general" vs "specific"
DETAIL_KEYWORDS = [
    "engine", "capacity", "weight", "spec", "specs", "specification",
    "hydraulic", "hydraulics", "emission", "model", "serial",
    "power", "hp", "horsepower", "load", "lifting",
    "payload", "dimensions", "width", "height", "length", "speed",
    "fuel", "consumption", "range", "torque", "ripper", "blade"
]

def is_specific_query(text):
    lower = text.lower()
    return any(k in lower for k in DETAIL_KEYWORDS)

# -------------------------------------
# PROCESS USER MESSAGE
# -------------------------------------

if prompt:
    # show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # classify
    cls = valid_prompt(prompt, model_id)

    # Greeting → simple reply
    if cls == "greet":
        answer = "Hello! I'm a heavy machinery assistant. What can I help you with?"
    # Not heavy machinery → reject
    elif cls == "other":
        answer = "I can only answer heavy machinery questions. Ask me about forklifts, excavators, bulldozers, etc."
    else:
        # heavy machinery → fetch KB only if specific
        if is_specific_query(prompt):
            kb_results = query_knowledge_base(prompt, kb_id)
        else:
            kb_results = []

        answer = generate_response(
            prompt, kb_results, model_id, temperature, top_p
        )

    # display assistant message
    with st.chat_message("assistant"):
        st.markdown(answer)

    # store assistant message
    st.session_state.messages.append({"role": "assistant", "content": answer})
