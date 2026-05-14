#!/bin/bash
cd /home/runner/workspace
exec uvicorn python_api.main:app --host 0.0.0.0 --port 8080 --reload
