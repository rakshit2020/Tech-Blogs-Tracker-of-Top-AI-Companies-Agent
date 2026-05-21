import truststore
truststore.inject_into_ssl()

from openai import OpenAI

import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("api_key")

client = OpenAI(
base_url=" ADD YOUR PREFERED BASE URL (EVEN LOCAL MODEL USING OLLAMA)",
api_key=api_key,
)


def llm_call(system_prompt: str, user_prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        extra_body={"thinking": {"type": "enabled", "budget_tokens": 5000}},
    )
    return completion.choices[0].message.content

