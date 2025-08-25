"""Async HTTP client with connection pooling and observability"""

import asyncio
import json
from typing import Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientConnectorError, ClientResponseError

from ..observability import get_logger, get_metrics


@dataclass
class HTTPResponse:
    """HTTP response wrapper"""
    status_code: int
    headers: Dict[str, str]
    body: Union[str, bytes]
    json_data: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None
    
    @property
    def is_success(self) -> bool:
        """Check if response indicates success"""
        return 200 <= self.status_code < 300
    
    @property
    def is_client_error(self) -> bool:
        """Check if response is a client error (4xx)"""
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self) -> bool:
        """Check if response is a server error (5xx)"""
        return 500 <= self.status_code < 600
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if response indicates rate limiting"""
        return self.status_code == 429
    
    def json(self) -> Dict[str, Any]:
        """Get JSON data from response"""
        if self.json_data is not None:
            return self.json_data
        
        if isinstance(self.body, str):
            return json.loads(self.body)
        else:
            return json.loads(self.body.decode('utf-8'))


class HTTPError(Exception):
    """HTTP-related errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        response: Optional[HTTPResponse] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
    
    @property
    def is_retryable(self) -> bool:
        """Check if error is potentially retryable"""
        if self.status_code is None:
            return True  # Network errors are retryable
        
        # Retry on server errors and rate limiting
        return self.status_code >= 500 or self.status_code == 429


class AsyncHTTPClient:
    """
    Async HTTP client with connection pooling, timeouts, and observability.
    
    Features:
    - Connection pooling and reuse
    - Configurable timeouts
    - Automatic JSON handling
    - Request/response logging
    - Metrics collection
    - Error handling and classification
    """
    
    def __init__(
        self,
        timeout_seconds: int = 30,
        max_connections: int = 100,
        max_connections_per_host: int = 10,
        keepalive_timeout: int = 30,
        enable_metrics: bool = True
    ):
        """
        Initialize HTTP client.
        
        Args:
            timeout_seconds: Request timeout
            max_connections: Maximum total connections
            max_connections_per_host: Maximum connections per host
            keepalive_timeout: Keep-alive timeout
            enable_metrics: Whether to collect metrics
        """
        self.timeout_seconds = timeout_seconds
        self.enable_metrics = enable_metrics
        
        # Configure connection settings
        connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections_per_host,
            keepalive_timeout=keepalive_timeout,
            enable_cleanup_closed=True
        )
        
        # Configure timeout
        timeout = ClientTimeout(total=timeout_seconds)
        
        # Create session
        self._session: Optional[ClientSession] = None
        self._connector = connector
        self._timeout = timeout
        
        # Observability
        self.logger = get_logger("http_client")
        if enable_metrics:
            self.metrics = get_metrics()
        else:
            self.metrics = None
    
    async def _get_session(self) -> ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                connector=self._connector,
                timeout=self._timeout,
                headers={'User-Agent': 'AI-Translation-Framework/2.0.0'}
            )
        return self._session
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """
        Make a GET request.
        
        Args:
            url: Request URL
            headers: Optional headers
            params: Optional query parameters
            timeout: Optional request timeout override
            
        Returns:
            HTTPResponse object
            
        Raises:
            HTTPError: On HTTP errors or network issues
        """
        return await self._request(
            method="GET",
            url=url,
            headers=headers,
            params=params,
            timeout=timeout
        )
    
    async def post(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """
        Make a POST request.
        
        Args:
            url: Request URL
            data: Request body data
            json_data: JSON data (will be serialized)
            headers: Optional headers
            timeout: Optional request timeout override
            
        Returns:
            HTTPResponse object
            
        Raises:
            HTTPError: On HTTP errors or network issues
        """
        return await self._request(
            method="POST",
            url=url,
            data=data,
            json_data=json_data,
            headers=headers,
            timeout=timeout
        )
    
    async def put(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """Make a PUT request"""
        return await self._request(
            method="PUT",
            url=url,
            data=data,
            json_data=json_data,
            headers=headers,
            timeout=timeout
        )
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """Make a DELETE request"""
        return await self._request(
            method="DELETE",
            url=url,
            headers=headers,
            timeout=timeout
        )
    
    async def _request(
        self,
        method: str,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """
        Make an HTTP request.
        
        Args:
            method: HTTP method
            url: Request URL
            data: Request body data
            json_data: JSON data
            headers: Request headers
            params: Query parameters
            timeout: Request timeout
            
        Returns:
            HTTPResponse object
            
        Raises:
            HTTPError: On HTTP errors or network issues
        """
        session = await self._get_session()
        
        # Prepare request
        request_headers = headers or {}
        request_timeout = timeout or self.timeout_seconds
        
        # Extract host for metrics
        host = url.split('/')[2] if '//' in url else 'unknown'
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.logger.debug(
                "Making HTTP request",
                method=method,
                url=url,
                timeout=request_timeout,
                has_data=data is not None or json_data is not None
            )
            
            # Make request
            async with session.request(
                method=method,
                url=url,
                data=data,
                json=json_data,
                headers=request_headers,
                params=params,
                timeout=ClientTimeout(total=request_timeout)
            ) as response:
                
                # Read response
                response_body = await response.read()
                end_time = asyncio.get_event_loop().time()
                response_time_ms = int((end_time - start_time) * 1000)
                
                # Parse JSON if content type indicates JSON
                json_response = None
                content_type = response.headers.get('content-type', '').lower()
                if 'application/json' in content_type:
                    try:
                        json_response = json.loads(response_body.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Not valid JSON, leave as None
                        pass
                
                # Create response object
                http_response = HTTPResponse(
                    status_code=response.status,
                    headers=dict(response.headers),
                    body=response_body.decode('utf-8') if response_body else '',
                    json_data=json_response,
                    response_time_ms=response_time_ms
                )
                
                # Log response
                self.logger.debug(
                    "HTTP request completed",
                    method=method,
                    url=url,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    response_size=len(response_body) if response_body else 0
                )
                
                # Record metrics
                if self.metrics:
                    self.metrics.increment_counter(
                        "http_requests_total",
                        labels={
                            "method": method,
                            "host": host,
                            "status_code": str(response.status)
                        }
                    )
                    self.metrics.observe_histogram(
                        "http_request_duration_seconds",
                        response_time_ms / 1000.0,
                        labels={"method": method, "host": host}
                    )
                
                # Check for HTTP errors
                if not http_response.is_success:
                    error_msg = f"HTTP {response.status} error for {method} {url}"
                    if json_response and 'error' in json_response:
                        error_msg += f": {json_response['error']}"
                    
                    self.logger.warning(
                        "HTTP request failed",
                        method=method,
                        url=url,
                        status_code=response.status,
                        error_message=error_msg
                    )
                    
                    raise HTTPError(error_msg, response.status, http_response)
                
                return http_response
                
        except ClientConnectorError as e:
            end_time = asyncio.get_event_loop().time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            error_msg = f"Connection error for {method} {url}: {e}"
            self.logger.error(
                "HTTP connection error",
                method=method,
                url=url,
                error=str(e),
                response_time_ms=response_time_ms
            )
            
            if self.metrics:
                self.metrics.increment_counter(
                    "http_requests_total",
                    labels={
                        "method": method,
                        "host": host,
                        "status_code": "connection_error"
                    }
                )
            
            raise HTTPError(error_msg)
            
        except asyncio.TimeoutError:
            end_time = asyncio.get_event_loop().time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            error_msg = f"Timeout for {method} {url} after {request_timeout}s"
            self.logger.error(
                "HTTP request timeout",
                method=method,
                url=url,
                timeout=request_timeout,
                response_time_ms=response_time_ms
            )
            
            if self.metrics:
                self.metrics.increment_counter(
                    "http_requests_total",
                    labels={
                        "method": method,
                        "host": host,
                        "status_code": "timeout"
                    }
                )
            
            raise HTTPError(error_msg)
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            error_msg = f"Unexpected error for {method} {url}: {e}"
            self.logger.error(
                "HTTP request error",
                method=method,
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                response_time_ms=response_time_ms
            )
            
            if self.metrics:
                self.metrics.increment_counter(
                    "http_requests_total",
                    labels={
                        "method": method,
                        "host": host,
                        "status_code": "error"
                    }
                )
            
            raise HTTPError(error_msg)
    
    async def close(self) -> None:
        """Close the HTTP client and clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()
        
        if self._connector:
            await self._connector.close()
        
        self.logger.debug("HTTP client closed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()