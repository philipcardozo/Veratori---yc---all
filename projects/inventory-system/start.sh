#!/bin/bash
# Kill any existing server on port 5001
lsof -ti:5001 | xargs kill -9 2>/dev/null
sleep 0.5
cd "/Users/felipecardozo/Desktop/Company Veratori /Veratori/projects/inventory-system"
"/Users/felipecardozo/Desktop/Company Veratori /Veratori/.venv/bin/python" camera_server.py
