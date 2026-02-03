#!/usr/bin/env python3
"""
Universal API Connector (#91)
Automatically connect to any API given documentation
"""
import requests
import json
from typing import Dict, Any, Optional

class UniversalAPIConnector:
    """Connect to any REST API automatically"""
   
    def __init__(self, base_url: str, api_key: Optional[str] = None, headers: Optional[Dict] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.default_headers = headers or {}
        if api_key:
            self.default_headers['Authorization'] = f'Bearer {api_key}'
   
    def request(self, method: str, endpoint: str, data: Any = None, params: Dict = None) -> Dict:
        """Make API request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.request(
            method=method.upper(),
            url=url,
            json=data if data else None,
            params=params,
            headers=self.default_headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json() if response.text else {}
   
    def get(self, endpoint: str, params: Dict = None) -> Dict:
        return self.request('GET', endpoint, params=params)
   
    def post(self, endpoint: str, data: Any) -> Dict:
        return self.request('POST', endpoint, data=data)
   
    def put(self, endpoint: str, data: Any) -> Dict:
        return self.request('PUT', endpoint, data=data)
   
    def delete(self, endpoint: str) -> Dict:
        return self.request('DELETE', endpoint)

# Example: Manus API
def create_manus_connector(api_key: str):
    return UniversalAPIConnector('https://api.manus.ai/v1', api_key)

if __name__ == "__main__":
    print("Universal API Connector ready")
