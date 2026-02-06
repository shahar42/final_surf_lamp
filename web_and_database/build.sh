#!/bin/bash
# Render build script for Surf Lamp Web Service
set -e

# Determine script location and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📦 Installing Python dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

echo "🔨 Building C++ message wrapper..."
cd "$REPO_ROOT/cpp_message_wrapper"
pip install -e .

echo "✅ Build complete!"
