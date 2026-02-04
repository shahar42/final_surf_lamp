#!/bin/bash
# Render build script for Surf Lamp Web Service
set -e

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🔨 Building C++ message wrapper..."
cd ../cpp_message_wrapper
pip install -e .
cd ../web_and_database

echo "✅ Build complete!"
