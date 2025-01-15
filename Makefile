# Makefile for using unified_context.py

.PHONY: help clean run-all run-compressed run-js-summary

# --------------------------------------------------------------------
# A self-documenting 'help' command
# --------------------------------------------------------------------
help:
	@echo "--------------------------------------------------------------------"
	@echo " Available make commands:"
	@echo "--------------------------------------------------------------------"
	@echo " make help               - Shows this help message"
	@echo " make run-all            - Runs the unified_context.py to gather all context into context.txt"
	@echo " make run-compressed     - Same as above but compresses the output into context.txt.gz"
	@echo " make run-js-summary     - Gathers a JSON summary of JS/TS code structure into js_summary.json"
	@echo " make clean              - Remove the context output files"
	@echo "--------------------------------------------------------------------"

# --------------------------------------------------------------------
# Basic usage
# --------------------------------------------------------------------
run-all:
	python unified_context.py --output context.txt

# --------------------------------------------------------------------
# Compressed usage
# --------------------------------------------------------------------
run-compressed:
	python unified_context.py --compress --output context.txt

# --------------------------------------------------------------------
# Gather JS/TS summary into JSON
# --------------------------------------------------------------------
run-js-summary:
	python unified_context.py --gather-js-summary js_summary.json

# --------------------------------------------------------------------
# Cleanup
# --------------------------------------------------------------------
clean:
	rm -f context.txt context.txt.gz js_summary.json .file_checksums.json
