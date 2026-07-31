#!/bin/bash
# Waifu Bot ishga tushirish skripti
cd "$(dirname "$0")"
pip install -r requirements.txt -q
python main.py
