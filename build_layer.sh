#!/bin/bash
# Build script for AWS Lambda X-Ray layer

set -e

LAYER_DIR="aws_lambda_layer"
BUILD_DIR="build/lambda-layer"
PACKAGE_NAME="xray-lambda-layer.zip"

echo "Building Lambda layer..."

# Clean build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy layer files
cp -r "$LAYER_DIR"/* "$BUILD_DIR/"

# Ensure correct structure
mkdir -p "$BUILD_DIR/bin"

# Create the layer package
cd "$BUILD_DIR"
zip -r "../../$PACKAGE_NAME" .
cd ../..

echo "Lambda layer package created: $PACKAGE_NAME"
echo ""
echo "To deploy this layer:"
echo "1. Upload $PACKAGE_NAME to AWS Lambda as a layer"
echo "2. Add the layer to your Lambda function"
echo "3. Set the environment variable: AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap"
echo "4. Optionally set XRAY_TRACING_ENABLED=true (default) or false"