#!/bin/bash

# Professional Lambda deployment package builder
set -e

echo "🔧 Building Lambda deployment package..."

# Clean previous builds
rm -rf package/ rag_indexer.zip

# Create package directory
mkdir -p package

# Install dependencies (download manylinux2014 cp39 wheels, then install locally)
echo "📦 Installing dependencies (manylinux2014 cp39 wheels)..."
rm -rf wheelhouse
mkdir -p wheelhouse

# Download prebuilt wheels compatible with Lambda (Python 3.9, manylinux2014, cp)
pip download -r requirements.txt \
  --dest wheelhouse \
  --only-binary=:all: \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 39 \
  --no-deps

# Install from local wheelhouse without hitting PyPI again
pip install -r requirements.txt -t package/ --no-index -f wheelhouse --no-cache-dir

# Copy source code
echo "📋 Copying source code..."
cp rag_indexer.py package/

# Copy shared modules from backend
cp ../backend/enhanced_rag_qwen.py package/ 2>/dev/null || echo "Warning: enhanced_rag_qwen.py not found"
cp ../backend/s3_cache.py package/ 2>/dev/null || echo "Warning: s3_cache.py not found"

# Remove unnecessary files to reduce package size
echo "🧹 Optimizing package size..."
find package/ -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find package/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find package/ -name "*.pyc" -delete 2>/dev/null || true
find package/ -name "*.pyo" -delete 2>/dev/null || true

# Remove documentation and examples
rm -rf package/*/examples/ 2>/dev/null || true
rm -rf package/*/docs/ 2>/dev/null || true
rm -rf package/*/*.egg-info/ 2>/dev/null || true

# Create deployment package
echo "📦 Creating deployment package..."
cd package
zip -r ../rag_indexer.zip . -x "*.DS_Store*" "*.git*"
cd ..

# Display package info
PACKAGE_SIZE=$(ls -lh rag_indexer.zip | awk '{print $5}')
echo "✅ Package created: rag_indexer.zip ($PACKAGE_SIZE)"

# Verify package contents
echo "📋 Package contents:"
unzip -l rag_indexer.zip | head -20

echo "🚀 Ready for Lambda deployment!"