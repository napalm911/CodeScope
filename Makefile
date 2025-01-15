# Makefile for CodeScope

.PHONY: help clean run-all run-compressed run-js-summary

help:
	@echo "--------------------------------------------------------------------"
	@echo " Available make commands:"
	@echo "--------------------------------------------------------------------"
	@echo " make help               - Shows this help message"
	@echo " make run-all            - Gathers all code context into context.txt"
	@echo " make run-compressed     - Same as above but compresses output into context.txt.gz"
	@echo " make run-js-summary     - Gathers JS/TS structure summary into js_summary.json"
	@echo " make clean              - Remove output files and checksum cache"
	@echo "--------------------------------------------------------------------"

run-all:
	python main.py --output context.txt

run-compressed:
	python main.py --compress --output context.txt

run-js-summary:
	python main.py --gather-js-summary js_summary.json

clean:
	rm -f context.txt context.txt.gz js_summary.json .file_checksums.json
