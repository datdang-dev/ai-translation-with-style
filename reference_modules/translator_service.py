import json
import copy
import requests

'''
@brief TranslatorService module - Handles translation workflow using API client and token counter.
@details
- Loads translation preset and manages translation requests.
- Parses streaming responses and logs translation progress.
@constructor
- @param api_client (APIClient): API client for sending requests.
- @param token_counter (TokenCounter): Token counter for counting tokens.
- @param preset_file (str): Path to translation preset JSON file.
- @param prefix (str): Prefix for translation prompt.
- @param logger (Logger): Logger for logging events.
@method
- `translate_text(text: str) -> str`
    - @param text (str): Text to translate.
    - @return (str): Translated text.
- `_parse_stream_response(response) -> str`
    - @param response: Streaming response from API.
    - @return (str): Parsed translated text.
'''
class TranslatorService:
    def __init__(self, api_client, token_counter, preset_file, prefix, logger):
        '''
        @brief Constructor for TranslatorService.
        @param api_client (APIClient): API client for sending requests.
        @param token_counter (TokenCounter): Token counter for counting tokens.
        @param preset_file (str): Path to translation preset JSON file.
        @param prefix (str): Prefix for translation prompt.
        @param logger (Logger): Logger for logging events.
        '''
        self.api_client = api_client
        self.token_counter = token_counter
        self.logger = logger
        with open(preset_file, 'r', encoding='utf-8') as f:
            self.preset = json.load(f)
        self.prefix = prefix

    def translate_text(self, text, max_retry_empty=3):
        '''
        @brief Translates the given text using the API client and preset.
        @param text (str): Text to translate.
        @return (str): Translated text.
        '''
        data = copy.deepcopy(self.preset)
        if 'messages' not in data or not isinstance(data['messages'], list):
            data['messages'] = []

        data['messages'].extend([
            {
                'role': 'assistant',
                'content': self.prefix + "\n"
            },
            {
                'role': 'user',
                'content': "\n" + text + "\n"
            },
        ])
        data['stream'] = True
        
        # ----------[DEBUG: LOG the requested prompts]----------#
        # Log the full prompt and all text sent to the model

        # prompt_log = "\n\n--- PROMPT TO MODEL ---\n\n"
        # for i, msg in enumerate(data['messages']):
        #     prompt_log += f"[{msg['role'].upper()}] {msg['content']}\n"
        # self.logger.info(prompt_log)

        retry_count = 0
        max_retry_stream = 3  # Retry cho stream errors
        while True:
            try:
                token_count = self.token_counter.count(data['messages'])
                self.logger.info(f"Sending translation request ({token_count} tokens)...")
                response = self.api_client.send_request(data)
                result = self._parse_stream_response(response)
                if result.strip():
                    return result
                retry_count += 1
                self.logger.warning(f"AI response is empty. Retrying translation (attempt {retry_count})...")
                if retry_count >= max_retry_empty:
                    self.logger.error(f"Failed to get non-empty translation after {max_retry_empty} attempts.")
                    # Treat repeated empty responses as fatal
                    raise RuntimeError(f"Empty AI response after {max_retry_empty} attempts")
            except (requests.exceptions.ChunkedEncodingError, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ReadTimeout) as e:
                retry_count += 1
                self.logger.warning(f"Stream connection error: {e}. Retrying request (attempt {retry_count})...")
                if retry_count >= max_retry_stream:
                    self.logger.error(f"Failed after {max_retry_stream} stream retries. Last error: {e}")
                    raise RuntimeError(f"Stream connection failed after {max_retry_stream} retries: {e}")

    def _parse_stream_response(self, response):
        '''
        @brief Parses the streaming response from the API and returns translated text.
        @param response: Streaming response from API.
        @return (str): Parsed translated text.
        '''
        full_response = ""
        buffer = ""

        self.logger.aispeak("======= AI TRANSLATION START =======")

        for line in response.iter_lines(decode_unicode=False):
            if not line:
                continue
            try:
                line = line.decode('utf-8')
            except UnicodeDecodeError:
                line = line.decode('utf-8', errors='ignore')

            if line.startswith('data: '):
                content = line[len('data: '):].strip()
                if content == '[DONE]':
                    break
                try:
                    chunk = json.loads(content)
                except json.JSONDecodeError:
                    continue

                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if delta:
                    buffer += delta
                    # Nếu có xuống dòng thì log từng dòng một
                    while '\n' in buffer:
                        line_out, buffer = buffer.split('\n', 1)
                        if line_out.strip():
                            self.logger.aispeak(line_out)
                        full_response += line_out + '\n'
        # Log phần còn lại nếu có
        if buffer.strip():
            self.logger.aispeak(buffer)
            full_response += buffer

        # Chuẩn hóa: bỏ các dòng trống và trim whitespace 2 đầu mỗi dòng
        result = "\n".join(
            l.strip() for l in full_response.replace("```", "").splitlines() if l.strip()
        )

        self.logger.aispeak("========= AI TRANSLATION END =========")

        self.logger.info("Translation completed.")
        return result
