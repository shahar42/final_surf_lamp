#!/usr/bin/env python3
"""
Simple wrapper to run Surf Lamp insights with custom output directory
Usage: python3 run_insights.py [output_directory]
"""

import asyncio
import sys
import os
from surf_lamp_insights import SurfLampInsights

async def main():
    # Get output directory from command line argument
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
        # Set environment variable to override config
        os.environ['INSIGHTS_OUTPUT_DIR'] = output_dir
        print(f"📁 Using custom output directory: {output_dir}")

    insights_generator = SurfLampInsights()

    print("🧠 Generating AI-powered surf lamp insights...")
    print(f"🔧 Configuration:")
    print(f"   - LLM: {insights_generator.llm_provider} ({insights_generator.model})")
    print(f"   - Output: {insights_generator.output_dir}/{insights_generator.output_format}")
    print(f"   - Analysis: {insights_generator.lookback_hours} hours")

    result = await insights_generator.generate_daily_insights()

    if result.get('insights_generated'):
        print("✅ Insights generated successfully!")
        print(f"📄 Report saved to: {insights_generator.output_dir}/")
        print(f"📊 Summary: {result.get('summary', {}).get('total_logs', 0)} logs analyzed")
    else:
        print("❌ Insights generation failed")
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())