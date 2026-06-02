#!/bin/bash

cd "$(dirname "$0")"

echo "🚀 Starting Streamlit App..."

./venv/bin/python -m streamlit run app.py
