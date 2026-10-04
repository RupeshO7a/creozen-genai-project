
import os

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Cloudflare Workers AI — embeddings
CLOUDFLARE_EMBED_MODEL = os.getenv(
    "CLOUDFLARE_EMBED_MODEL",
    "@cf/qwen/qwen3-embedding-0.6b",
)

EMBED_DIM = 1024

# OpenRouter — chat generation
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free",
)

CLOUDFLARE_TIMEOUT = 60


def embed(texts, task_type=None):
    """Generate 1024-dimensional embeddings using Cloudflare Workers AI."""

    if isinstance(texts, str):
        texts = [texts]

    if not texts:
        return []

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not account_id or not api_token:
        raise RuntimeError(
            "CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN "
            "is missing from backend/.env."
        )

    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/{CLOUDFLARE_EMBED_MODEL}"
    )

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json={"text": texts},
            timeout=CLOUDFLARE_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Cloudflare embedding request failed: {exc}"
        ) from exc

    if not payload.get("success", False):
        errors = payload.get("errors", [])
        raise RuntimeError(f"Cloudflare AI error: {errors}")

    vectors = payload.get("result", {}).get("data")

    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise RuntimeError(
            "Cloudflare returned an unexpected number of embeddings."
        )

    for index, vector in enumerate(vectors):
        if not isinstance(vector, list) or len(vector) != EMBED_DIM:
            actual = len(vector) if isinstance(vector, list) else "unknown"
            raise RuntimeError(
                f"Embedding {index} has {actual} dimensions; "
                f"expected {EMBED_DIM}."
            )

    return vectors


def get_openrouter_client():
    """Create the OpenRouter client for answer generation."""

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing from backend/.env "
            "or the hosting environment."
        )

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def generate_response(messages, tools=None):
    """Generate a chat response through OpenRouter."""

    client = get_openrouter_client()

    kwargs = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
    }

    if tools:
        kwargs["tools"] = tools

    response = client.chat.completions.create(**kwargs)

    if not response.choices:
        raise RuntimeError(
            "The model provider returned no response choices."
        )

    assistant_message = response.choices[0].message

    message = {
        "role": "assistant",
        "content": assistant_message.content or "",
    }

    if assistant_message.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in assistant_message.tool_calls
        ]

    return {"message": message}
