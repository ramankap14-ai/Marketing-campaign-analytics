#!/usr/bin/env bash
set -e
python src/01_clean_load.py
python src/02_statistics.py
python src/03_model_targeting.py
