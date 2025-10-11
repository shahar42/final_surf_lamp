#!/bin/bash
# Surf Lamp Daily Summary - Runs every day at 8 PM
# Generates AI-powered daily insights and sends comprehensive email report

cd /home/shahar42/Git_Surf_Lamp_Agent
source esurf/bin/activate
python3 run_daily_insights.py >> insights_cron.log 2>&1
