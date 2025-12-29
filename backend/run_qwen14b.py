#!/usr/bin/env python3
import time
import os
from dotenv import load_dotenv
from llama_cpp import Llama

load_dotenv()

def stream_generate(llm, prompt):
    """Generates tokens one by one using llama.cpp"""
    stream = llm.create_completion(
        prompt,
        stream=True,
        temperature=0.7,
        top_k=40,
        top_p=0.95,
        max_tokens=5000,
    )

    start_time = time.time()
    tokens_generated = 0
    print("Response: ", end="", flush=True)

    for output in stream:
        text_chunk = output['choices'][0]['text']
        print(text_chunk, end="", flush=True)
        tokens_generated += 1

    end_time = time.time()
    elapsed = end_time - start_time
    speed = tokens_generated / elapsed if elapsed > 0 else float('inf')
    print(f"\n[Generation speed: {speed:.2f} tokens/sec]")

def main():
    api_key = os.getenv("TOGETHER_AI_API_KEY")
    model_id = os.getenv("MODEL_ID")
    if not api_key or not model_id:
        print("Missing Together AI API key or MODEL_ID in the environment variables!")
        exit(1)
    print(f"Loading model {model_id} using Together AI API...")
    
    # Initialize model with GPU acceleration via API
    llm = Llama(
        api_key=api_key,
        model=model_id,
        n_gpu_layers=43,
        n_ctx=2048,
        n_threads=8,
        verbose=False
    )

    print("Model loaded. Type 'quit' to exit.\n")
    while True:
        prompt = input("Enter your prompt: ").strip()
        if prompt.lower() in {"quit", "exit"}:
            break
        stream_generate(llm, prompt)
        print("\n")

if __name__ == "__main__":
    main()

