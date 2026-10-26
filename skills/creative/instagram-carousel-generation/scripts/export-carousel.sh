#!/bin/bash
# Export Instagram carousel from HTML using html-to-carousel tool
# Usage: ./export-carousel.sh /path/to/carousel.html /path/to/output-dir

set -e

HTML_FILE="${1:-/home/opc/claude-code-carousel.html}"
OUTPUT_DIR="${2:-/home/opc/carousel-output}"
TOOL_DIR="/tmp/html-to-carousel"

echo "📦 Exporting carousel from $HTML_FILE to $OUTPUT_DIR"

cd "$TOOL_DIR"
python3 main.py "$HTML_FILE" --output-dir "$OUTPUT_DIR"

echo "✅ Export complete. Files:"
ls -la "$OUTPUT_DIR"/*.png

echo ""
echo "📁 Creating ZIP..."
cd "$OUTPUT_DIR"
zip -r "${OUTPUT_DIR}.zip" *.png

echo "✅ ZIP created: ${OUTPUT_DIR}.zip"