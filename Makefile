VARS_OLD := $(.VARIABLES)

BUILD_DIR := build
DIST_DIR := dist
LAYER_SRC_FILES := $(shell find aws_lambda_layer -type f)
PWD := $(shell pwd)

all: $(DIST_DIR)/layer.zip

$(DIST_DIR)/layer.zip: $(BUILD_DIR)/layer
	@mkdir -p $(DIST_DIR)
	cd $(BUILD_DIR)/layer && zip -r $(PWD)/$@ *

$(BUILD_DIR)/layer: $(LAYER_SRC_FILES) uv.lock
	@mkdir -p $@
	@mkdir -p $@/bin/python-packages
	cp -r aws_lambda_layer/* $@
	cat pyproject.toml | uv run toml2json | jq -r '.project.dependencies | .[]' | while read -r req; do \
		pip download $$req -d $@/bin/python-packages --no-deps; \
	done
	for file in $@/bin/python-packages/*; do \
		unzip -o $$file -d $@/bin/python; \
	done
	rm -rf $@/requirements.txt
	rm -rf $@/bin/python-packages

clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(DIST_DIR)