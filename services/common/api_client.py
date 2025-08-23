from abc import ABC, abstractmethod
import aiohttp
import json

class APIClient(ABC): # pragma: no cover, abstract class
    @abstractmethod
    async def send_request(self, data): # pragma: no cover, abstract method
        pass

'''
@brief OpenRouterClient module - Client for interacting with OpenRouter API, automatic API key management, advanced logging.
@details
- Sends requests and automatically switches API keys when rate-limited.
- Provides detailed logging for easier debugging.
- Inherits from APIClient and extends its functionality.
@constructor
- @param api_key_manager (APIKeyManager): Manages the pool of API keys.
- @param api_url (str): API endpoint URL.
- @param logger (Logger): Logger object for logging.
@method
- `send_request(payload: dict) -> dict`
    - @param payload (dict): Data to send to the API.
    - @return (dict): JSON response from the API.
    - @raises Exception: If the request fails or all keys are exhausted.
'''
class OpenRouterClient(APIClient):
    def __init__(self, api_key_manager, api_url, logger):
        '''
        @brief Constructor for OpenRouterClient.
        @param api_key_manager (APIKeyManager): Manages API keys.
        @param api_url (str): API endpoint URL.
        @param logger (Logger): Logger for logging events.
        '''
        self.api_key_manager = api_key_manager
        self.api_url = api_url
        self.logger = logger

    async def send_request(self, data):
        '''
        @brief Send an async request to the OpenRouter API.
        @param data (dict): Payload to send to the API.
        @return (dict): JSON response from the API.
        @raises Exception: If all API keys are exhausted or request fails.
        '''
        last_error = None
        async with aiohttp.ClientSession() as session:
            while True:
                key_info = await self.api_key_manager.get_next_available_key()
                if not key_info:
                    self.logger.error("No available API key")
                    raise RuntimeError("No available API key")
                
                key = key_info['key']
                self.logger.info(f"Using API key...")
                
                # Logging remains synchronous but quick
                service_name = 'OpenRouter'
                model_name = data.get('model', 'unknown')
                self.logger.info(f"Using Translation Service: {service_name} | Model: {model_name}")

                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                
                # Nếu là streaming request, xử lý khác
                is_streaming = data.get('stream', False)
                
                try:
                    if is_streaming:
                        async with session.post(
                            self.api_url,
                            headers=headers,
                            json=data,
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            response.status_code = response.status
                            
                            if response.status_code == 200:
                                # Xử lý streaming response
                                full_response = ""
                                buffer = ""
                                
                                # Log bắt đầu dịch
                                self.logger.aispeak("======= AI TRANSLATION START =======")
                                
                                async for line in response.content:
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
                                        except json.JSONDecodeError as e:
                                            self.logger.warning(f"Failed to parse JSON from streaming response: {e}")
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
                                
                                # Log kết thúc dịch
                                self.logger.aispeak("========= AI TRANSLATION END =========")
                                
                                # Trả về response với nội dung đã xử lý
                                return {
                                    "choices": [
                                        {
                                            "message": {
                                                "content": full_response.strip()
                                            }
                                        }
                                    ]
                                }
                            
                            if response.status_code == 429 or "Rate limit exceeded" in (await response.text()):
                                # Only switch key if rate limit
                                response_text = await response.text()
                                last_error = response_text
                                self.logger.warning(f"Key rate-limited, switching...")
                                await self.api_key_manager.report_key_error(key, response.status_code)
                                continue
                            elif response.status_code >= 500:
                                # Server error: fail immediately (no backoff)
                                response_text = await response.text()
                                last_error = response_text
                                self.logger.error(f"API server error {response.status_code}: {response_text[:200]}")
                                await self.api_key_manager.report_key_error(key, response.status_code)
                                raise RuntimeError(f"API server error {response.status_code}")
                            else:
                                # Other client errors: fail immediately
                                response_text = await response.text()
                                last_error = response_text
                                self.logger.error(f"API error {response.status_code}: {response_text[:200]}")
                                await self.api_key_manager.report_key_error(key, response.status_code)
                                raise RuntimeError(f"API error {response.status_code}")
                    else:
                        # Xử lý non-streaming request
                        async with session.post(
                            self.api_url,
                            headers=headers,
                            json=data,
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            # Read response content immediately
                            response_text = await response.text()
                            response.status_code = response.status
                            
                            if response.status_code == 200:
                                try:
                                    return json.loads(response_text)
                                except json.JSONDecodeError as e:
                                    self.logger.error(f"Failed to parse JSON response: {e}")
                                    raise RuntimeError(f"Failed to parse JSON response: {e}")
                            
                            if response.status_code == 429 or "Rate limit exceeded" in response_text:
                                # Only switch key if rate limit
                                last_error = response_text
                                self.logger.warning(f"Key rate-limited, switching...")
                                await self.api_key_manager.report_key_error(key, response.status_code)
                                continue
                            elif response.status_code >= 500:
                                # Server error: fail immediately (no backoff)
                                last_error = response_text
                                self.logger.error(f"API server error {response.status_code}: {response_text[:200]}")
                                await self.api_key_manager.report_key_error(key, response.status_code)
                                raise RuntimeError(f"API server error {response.status_code}")
                            else:
                                # Other client errors: fail immediately
                                last_error = response_text
                                self.logger.error(f"API error {response.status_code}: {response_text[:200]}")
                                await self.api_key_manager.report_key_error(key, response.status_code)
                                raise RuntimeError(f"API error {response.status_code}")
                except aiohttp.ClientError as e:
                    last_error = str(e)
                    self.logger.error(f"Connection error: {e}")
                    # No backoff/rotation on connection error per requirement
                    raise RuntimeError(f"API connection error: {e}")
