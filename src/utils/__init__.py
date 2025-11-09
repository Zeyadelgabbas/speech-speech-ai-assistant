from .logger import get_logger
from .config import config , Config
import tiktoken


__all__ = [
    'get_logger',
    'config',
    'Config',
    'count_tokens'
]


def count_toknes(text: str , model :str = config.OPENAI_MODEL) ->int:

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

