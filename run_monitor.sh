#!/bin/bash
# Surf Lamp Health Monitor - Runs every 2 hours
# Checks system health and sends email alerts if issues detected

cd /home/shahar42/Git_Surf_Lamp_Agent
source myenv/bin/activate
python3 surf_lamp_monitor.py --test >> monitor_cron.log 2>&1
