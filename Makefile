# AWS Lambda Layer Makefile for X-Ray Instrumentation
#
# This Makefile builds a minimal Lambda layer that automatically instruments
# Python code with AWS X-Ray tracing. The layer includes only the necessary
# dependencies (aws-xray-sdk and wrapt) while relying on the Lambda runtime
# to provide botocore (>=1.11.3).
#
# Build process:
# 1. Copies layer source files (bootstrap, sitecustomize.py)
# 2. Downloads only aws-xray-sdk and wrapt packages (not botocore)
# 3. Extracts packages to /opt/bin/python for runtime access
# 4. Creates a deployable layer.zip file

VARS_OLD := $(.VARIABLES)

BUILD_DIR := build
DIST_DIR := dist
LAYER_SRC_FILES := $(shell find aws_lambda_layer -type f)
PWD := $(shell pwd)

# Default target: build the layer zip file
all: $(DIST_DIR)/layer.zip

init:
	uv sync --dev

# Create the final layer zip file from the built layer directory
$(DIST_DIR)/layer.zip: $(BUILD_DIR)/layer
	@mkdir -p $(DIST_DIR)
	cd $(BUILD_DIR)/layer && zip -r $(PWD)/$@ *

# Build the layer directory with all necessary files and dependencies
$(BUILD_DIR)/layer: $(LAYER_SRC_FILES) uv.lock
	@mkdir -p $@
	@mkdir -p $@/bin/python-packages
	
	# Copy layer source files (bootstrap script and sitecustomize.py)
	cp -r aws_lambda_layer/* $@
	
	# Download only the dependencies listed in pyproject.toml
	# This includes aws-xray-sdk and wrapt, but NOT botocore
	# botocore is provided by the Lambda runtime (>=1.11.3)
	cat pyproject.toml | uv run toml2json | jq -r '.project.dependencies | .[]' | while read -r req; do \
		pip download $$req -d $@/bin/python-packages --no-deps; \
	done
	
	# Extract downloaded packages to /opt/bin/python (layer's Python path)
	for file in $@/bin/python-packages/*; do \
		unzip -o $$file -d $@/bin/python; \
	done
	
	# Clean up temporary files
	rm -rf $@/requirements.txt
	rm -rf $@/bin/python-packages

# Clean up build artifacts
clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(DIST_DIR)