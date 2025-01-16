#!/usr/bin/env python3
import os
import json
import argparse
from pathlib import Path

import openai
import tiktoken  # for accurate token counting

def get_args():
    parser = argparse.ArgumentParser(description="Send files to ChatGPT for analysis based on a pre-prompt.")
    parser.add_argument(
        "--project_dir",
        required=True,
        help="Path to the directory that contains the source files you want to process."
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="The question or instructions you want to ask ChatGPT about each file."
    )
    parser.add_argument(
        "--output",
        default="results.json",
        help="Name of the JSON file where ChatGPT responses will be stored."
    )
    parser.add_argument(
        "--api_key",
        default=None,
        help="OpenAI API key. If not provided, will use OPENAI_API_KEY environment variable."
    )
    parser.add_argument(
        "--model",
        default="gpt-3.5-turbo",
        help="Which OpenAI Chat model to use by default (gpt-3.5-turbo, gpt-4, etc.)."
    )
    parser.add_argument(
        "--file_extensions",
        nargs="*",
        default=[".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".wasm", ".py"],
        help="List of file extensions to include."
    )
    return parser.parse_args()


def read_file_content(file_path):
    """
    Safely read file text (skip binary, unreadable, etc.).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def get_token_count_for_message(model_name, prompt_content):
    """
    Get approximate token count for a single message using tiktoken.
    The tokens used in a chat completion also include system, user, assistant roles, etc.
    But for a rough estimate, let's just measure the content + prompt overhead.
    """
    # Example encoding to handle standard ChatGPT models
    encoding = tiktoken.encoding_for_model(model_name)
    tokens = encoding.encode(prompt_content)
    return len(tokens)


def estimate_costs_for_models(total_tokens):
    """
    Estimate cost for 3 specific models, for demonstration.
    We'll use approximate input cost only.
    If you want to be thorough, incorporate both input + output tokens.

    Prices (as of Q4 2023, subject to change!):
      - gpt-3.5-turbo: ~$0.0015 / 1K tokens input
      - gpt-3.5-turbo-16k: ~$0.003 / 1K tokens input
      - gpt-4 (8k context): ~$0.03 / 1K tokens input
    """
    # Convert total tokens to thousands
    thousand_tokens = total_tokens / 1000.0

    # approximate pricing
    pricing = {
        "gpt-3.5-turbo": 0.0015,
        "gpt-3.5-turbo-16k": 0.003,
        "gpt-4": 0.03
    }

    estimates = {}
    for model, cost_per_1k in pricing.items():
        estimate_dollars = thousand_tokens * cost_per_1k
        estimates[model] = estimate_dollars

    return estimates


def analyze_file_with_chatgpt(file_path, file_content, prompt, model):
    """
    Send the file content plus your pre-prompt to the ChatGPT API and get the response.
    """
    # Construct conversation with system + user
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that analyzes source code files. "
                       "You should read the content of the file carefully, "
                       "then answer questions or perform tasks related to the file."
        },
        {
            "role": "user",
            "content": f"{prompt}\n\n---\nFile content:\n{file_content}"
        }
    ]

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error calling OpenAI API for file {file_path}: {e}")
        return None


def main():
    args = get_args()

    # Setup API Key
    if args.api_key:
        openai.api_key = args.api_key
    else:
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("No OpenAI API key provided. Either set --api_key or set OPENAI_API_KEY in your environment.")
        openai.api_key = os.environ["OPENAI_API_KEY"]

    project_dir = Path(args.project_dir).resolve()
    output_path = Path(args.output).resolve()

    # 1) Gather files & content
    file_contents = []
    for root, dirs, files in os.walk(project_dir):
        for filename in files:
            file_ext = os.path.splitext(filename)[1]
            if file_ext.lower() in [ext.lower() for ext in args.file_extensions]:
                file_path = Path(root, filename)
                content = read_file_content(file_path)
                if content is not None:
                    file_contents.append((file_path, content))

    # 2) Count total tokens (rough estimate) for all files with the prompt
    # Let's do a single combined prompt approach for cost estimates: 
    #  We'll approximate that each file is processed separately with a user message 
    #  that includes both the question and the file content. 
    # This is a rough approach, actual usage might differ if you chunk content.
    total_tokens = 0
    for file_path, content in file_contents:
        user_message = f"{args.prompt}\n\n---\nFile content:\n{content}"
        # We'll add overhead for system message. Let's just do a minimal approach:
        system_message = ("You are a helpful assistant that analyzes source code files.")
        # combined content for counting
        combined_content = system_message + "\n\n" + user_message
        # Count tokens for the default model (or pick a standard reference like "gpt-3.5-turbo")
        tokens_for_this_file = get_token_count_for_message("gpt-3.5-turbo", combined_content)
        total_tokens += tokens_for_this_file

    # 3) Estimate cost for 3 known models
    estimates = estimate_costs_for_models(total_tokens)

    print("=== Estimated Costs (Input Tokens Only) ===")
    print(f"Total tokens across all files: {total_tokens}")
    for m, cost in estimates.items():
        print(f"  {m}: ~${cost:.4f}")

    # 4) Ask for user confirmation
    proceed = input("Proceed with API calls? (y/n): ")
    if proceed.lower() != 'y':
        print("Aborted by user.")
        return

    # 5) If confirmed, proceed with actual calls
    all_responses = []
    for file_path, content in file_contents:
        response = analyze_file_with_chatgpt(
            file_path=file_path,
            file_content=content,
            prompt=args.prompt,
            model=args.model,
        )
        if response:
            result = {
                "file_path": str(file_path.relative_to(project_dir)),
                "prompt": args.prompt,
                "response": response,
            }
            all_responses.append(result)
            print(f"[OK] Processed {file_path}")
        else:
            print(f"[SKIP] {file_path} due to API error.")

    # 6) Save all responses to JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_responses, f, indent=4, ensure_ascii=False)

    print(f"\nAnalysis complete. Results saved to {output_path}.")


if __name__ == "__main__":
    main()