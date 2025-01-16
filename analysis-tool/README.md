# My Analysis Tool

This project provides a Python script and Makefile to automate scanning through source files, 
estimating ChatGPT token usage costs for multiple models, and optionally sending the content 
to the OpenAI ChatCompletion API.

## Installation

1. **Install Poetry** if you haven't already:
   ```bash
   pip install poetry

	2.	Install dependencies:

make install

This will run poetry install and set up a virtual environment with the required packages.

Usage

1. Estimate Tokens & Confirm

By default, when you run the script, it will:
	•	Scan your project directory (recursively).
	•	Count tokens for the included files.
	•	Estimate cost for 3 models (e.g., `gpt-3.5-turbo`, `gpt-3.5-turbo-16k`, and `gpt-4`).
	•	Ask you to confirm whether to proceed with the actual API calls.

2. Run

You can use the Makefile for convenience:

make run PROJECT_DIR=/path/to/your/code PROMPT="Will this file need to be changed from JS to WASM?" API_KEY="your-openai-key"

Alternatively, you can run the script directly:

poetry run python scripts/process_files_with_chatgpt.py \
    --project_dir /path/to/your/code \
    --prompt "Will this file need to be changed from JS to WASM?" \
    --api_key "your-openai-key" \
    --model "gpt-3.5-turbo" \
    --output results.json

After confirming, the script will go file by file, ask ChatGPT with your prompt, and store the responses in a JSON file.

3. Customization

You can customize:
	•	File extensions to scan.
	•	Output file location and format.
	•	Models to estimate cost for.
	•	Prompt text.

4. Additional Info
	•	Token Calculation is done using the `tiktoken` library for a more accurate count.
	•	Cost Estimation is approximate based on OpenAI’s listed prices.
	•	API Key can be set in the environment as `OPENAI_API_KEY` or passed via `–api_key`.

License

MIT