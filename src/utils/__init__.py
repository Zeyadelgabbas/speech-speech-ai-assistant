from .logger import get_logger
from .config import config , Config
import tiktoken
from typing import Dict , Any


__all__ = [
    'get_logger',
    'config',
    'Config',
    'count_tokens'
]


def count_tokens(text: str , model :str = config.OPENAI_MODEL) ->int:

    """ input : string , output: number of tokens"""
    try:
        # Get the encoding for the model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback if the model is not found
        encoding = tiktoken.get_encoding("cl100k_base")
    
    # Encode the text and count tokens
    num_tokens = len(encoding.encode(text))
    return num_tokens



def estimate_cost(tokens: Dict[str,Any], model_name: str=None):
    """
    Estimate token counts and cost using tiktoken + OpenAI pricing.
    """
    MODEL_PRICES = config.MODEL_PRICES
    model_name = model_name or config.OPENAI_MODEL

    prompt_tokens = tokens['prompt_tokens']
    completion_tokens = tokens['completion_tokens']
    total_tokens = prompt_tokens + completion_tokens

    if model_name not in MODEL_PRICES:
        return {
        "model": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_cost_usd": 0,
        "completion_cost_usd": 0,
        "total_cost_usd": 0,
    }
    
    # Pricing
    price = MODEL_PRICES[model_name]
    prompt_cost = (prompt_tokens / 1_000_000) *float(price["prompt"]) 
    completion_cost = (completion_tokens / 1_000_000) *float(price["completion"])
    total_cost = prompt_cost + completion_cost

    return {
        "model": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_cost_usd": prompt_cost,
        "completion_cost_usd": completion_cost,
        "total_cost_usd": total_cost,
    }



