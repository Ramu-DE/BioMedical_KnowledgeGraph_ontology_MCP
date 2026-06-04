"""AWS SigV4 authenticator for Neptune HTTP endpoints."""

from typing import Dict, Optional
from urllib.parse import urlparse

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


class SigV4Authenticator:
    """
    AWS Signature Version 4 authenticator for Neptune.
    
    Signs HTTP requests to Neptune SPARQL and openCypher endpoints using IAM credentials.
    Supports AWS credential chain: environment variables, instance profile, assumed role.
    """
    
    def __init__(self, region: str, service_name: str = "neptune-db"):
        """
        Initialize SigV4 authenticator.
        
        Args:
            region: AWS region (e.g., "us-east-1")
            service_name: AWS service name (default: "neptune-db")
        """
        self.region = region
        self.service_name = service_name
        
        # Get credentials from AWS credential chain
        session = boto3.Session()
        self.credentials = session.get_credentials()
    
    def sign_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Sign HTTP request with SigV4.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: HTTP headers
            body: Request body
            
        Returns:
            Dictionary of signed headers including Authorization header
        """
        # Parse URL
        parsed = urlparse(url)
        
        # Create AWS request
        request = AWSRequest(
            method=method,
            url=url,
            headers=headers or {},
            data=body,
        )
        
        # Create SigV4 signer
        signer = SigV4Auth(self.credentials, self.service_name, self.region)
        
        # Sign the request
        signer.add_auth(request)
        
        # Return signed headers
        return dict(request.headers)
