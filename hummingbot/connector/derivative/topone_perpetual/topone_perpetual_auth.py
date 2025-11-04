import hashlib
import json
from typing import Any, Dict
from urllib.parse import urlencode

from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest, WSRequest


class TopOnePerpetualAuth(AuthBase):
    """
    Auth class for TopOne exchange
    Based on TopOne API documentation signature method:
    X-Openapi-Sign = SHA256(Method=%s&Path=%s&Timestamp=%s&Secret=%s)
    """
    
    def __init__(self, api_key: str, secret_key: str, time_provider: TimeSynchronizer):
        self.api_key = api_key
        self.secret_key = secret_key
        self.time_provider = time_provider

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        """
        Adds the server time and the signature to the request, required for authenticated interactions.
        According to TopOne API docs, we need to add headers:
        - X-Time: timestamp in milliseconds
        - X-Openapi-Key: API key
        - X-Openapi-Sign: SHA256 signature
        
        :param request: the request to be configured for authenticated interaction
        """
        headers = {}
        if request.headers is not None:
            headers.update(request.headers)
        
        # Add authentication headers
        headers.update(self.header_for_authentication(request))
        request.headers = headers

        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        """
        This method is intended to configure a websocket request to be authenticated.
        TopOne WebSocket authentication details need to be confirmed from documentation.
        """
        return request  # pass-through for now

    def header_for_authentication(self, request: RESTRequest) -> Dict[str, str]:
        """
        Generates the authentication headers required by TopOne API
        """
        # Get current timestamp in milliseconds
        timestamp = int(self.time_provider.time() * 1000)
        
        # Generate signature based on TopOne's method
        signature = self._generate_signature(
            method=request.method.value.upper(),
            path=request.url,
            timestamp=str(timestamp)
        )
        
        return {
            "X-Time": str(timestamp),
            "X-Openapi-Key": self.api_key,
            "X-Openapi-Sign": signature,
            "Content-Type": "application/json"
        }

    def _generate_signature(self, method: str, path: str, timestamp: str) -> str:
        """
        Generate signature according to TopOne API documentation:
        X-Openapi-Sign = SHA256(Method=%s&Path=%s&Timestamp=%s&Secret=%s)
        
        Example from docs:
        Method=GET&Path=/api/v1/server-time&Timestamp=1748095101543&Secret=1533a8d407b17ddd4ecdd3cdbc37bf34c4a47beabca0a97bff00b253a0683ce2
        """
        # Extract path from full URL if needed
        if path.startswith("http"):
            from urllib.parse import urlparse
            parsed_url = urlparse(path)
            path = parsed_url.path
            if parsed_url.query:
                path += "?" + parsed_url.query
        
        # Create signature string according to TopOne format
        signature_string = f"Method={method}&Path={path}&Timestamp={timestamp}&Secret={self.secret_key}"
        
        # Generate SHA256 hash
        signature = hashlib.sha256(signature_string.encode('utf-8')).hexdigest()
        
        return signature

    def add_auth_to_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add authentication parameters to request params if needed
        TopOne seems to use headers for auth, but keeping this for compatibility
        """
        return params or {}