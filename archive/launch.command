#!/bin/bash

cd "$(dirname "$0")"

echo "🚀 Starting Quant App..."

source venv/bin/activate

streamlit run app.py

