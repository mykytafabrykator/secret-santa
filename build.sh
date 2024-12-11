#!/usr/bin/env bash
set -e

pip install --upgrade pip
pip install -r requirements.txt

if [ -z "$BOT_TOKEN" ]; then
  echo "BOT_TOKEN is not set. Please set this environment variable."
  exit 1
fi

if [ -z "$POSTGRES_DSN" ]; then
  echo "POSTGRES_DSN is not set. Please set this environment variable."
  exit 1
fi

python main.py

echo "Build completed successfully!"
