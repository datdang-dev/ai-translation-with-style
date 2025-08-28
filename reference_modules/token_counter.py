from transformers import AutoTokenizer

'''
@brief TokenCounter module - Counts tokens in messages using a specified tokenizer model.
@details
- Uses HuggingFace tokenizer to count tokens in message lists.
@constructor
- @param logger (Logger): Logger for logging events.
- @param model_name (str): Name of the tokenizer model.
@method
- `count(messages: list) -> int`
    - @param messages (list): List of message dicts.
    - @return (int): Number of tokens in all messages.
'''
class TokenCounter:
    def __init__(self, logger, model_name="gpt2"):
        '''
        @brief Constructor for TokenCounter.
        @param logger (Logger): Logger for logging events.
        @param model_name (str): Name of the tokenizer model.
        '''
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.logger = logger

    def count(self, messages):
        '''
        @brief Counts the number of tokens in a list of messages.
        @param messages (list): List of message dicts.
        @return (int): Number of tokens in all messages.
        '''
        full_text = "".join(f"{m['role']}: {m['content']}\n" for m in messages)
        count = len(self.tokenizer.encode(full_text))
        self.logger.debug(f"Token count: {count}")
        return count
