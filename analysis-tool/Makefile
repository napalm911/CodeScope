# Makefile for my-analysis-tool

.PHONY: help install run

help:  ## Show this help message
	@echo "Available commands:"
	@echo "  make install   - Install dependencies via Poetry"
	@echo "  make run       - Run the analysis script"
	@echo "  make help      - Show this help message"

install:  ## Install dependencies via Poetry
	poetry install

run:  ## Run the analysis script
	# Example usage:
	# make run PROJECT_DIR=/path/to/source PROMPT="Your question"
	poetry run python scripts/process_files_with_chatgpt.py \
		--project_dir "$(PROJECT_DIR)" \
		--prompt "$(PROMPT)" \
		--output "$(OUTPUT)" \
		--model "gpt-3.5-turbo" \
		--api_key "$(API_KEY)"