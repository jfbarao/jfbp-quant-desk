# =========================================================
# 🚀 JFBP STREAMLIT ENTRYPOINT (STABLE)
# =========================================================

from pathlib import Path
import sys
import streamlit as st

# =========================================================
# FORCE PROJECT ROOT
# =========================================================

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# =========================================================
# IMPORT APP ROUTER (IMPORTANT: NO FUNCTION CALL HERE)
# =========================================================

import app


# =========================================================
# STREAMLIT ENTRY
# =========================================================

if __name__ == "__main__":
    app.app()