import random, threading, queue, time
import streamlit as st
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# 1)   charger le fichier  (remplacez par votre propre fonction) ------------
# ---------------------------------------------------------------------------
@st.cache_data
def load_sheets() -> dict:
    time.sleep(0.5)          # simulation 0,5 s
    return {"ok":"data"}

# ---------------------------------------------------------------------------
# 2)   fonction qui plante ou réussit ---------------------------------------
# ---------------------------------------------------------------------------
def build_sheet(data):
    time.sleep(2)            # simulation longue
    if random.random() < .2:
        raise RuntimeError("échec du tirage")
    return ["MOT1","MOT2"]

# ---------------------------------------------------------------------------
def worker(q: queue.Queue, data):
    try:
        res = build_sheet(data)
        q.put(("OK", res))
    except Exception as e:
        q.put(("ERR", str(e)))

# ---------------------------------------------------------------------------
if "status" not in st.session_state:
    st.session_state.status = "building"
    st.session_state.q = queue.Queue(maxsize=1)
    th = threading.Thread(target=worker,
                          args=(st.session_state.q, load_sheets()),
                          daemon=True)
    th.start()

st.write("Status :", st.session_state.status)
if st.session_state.status == "building":
    try:
        msg = st.session_state.q.get_nowait()
        if msg[0] == "OK":
            st.session_state.result = msg[1]
            st.session_state.status = "ready"
        else:
            st.session_state.error = msg[1]
            st.session_state.status = "error"
        st.experimental_rerun()
    except queue.Empty:
        st.write("…toujours en cours")

elif st.session_state.status == "ready":
    st.success("TIRAGE OK :", st.session_state.result)

else:
    st.error("ERREUR :", st.session_state.error)
