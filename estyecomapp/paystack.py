import requests
import logging
from django.conf import settings
from django.core.cache import cache
from typing import Tuple, Optional, Dict, Any
import time

logger = logging.getLogger(__name__)

class Paystack:
    """Optimized Paystack integration with caching and retry logic"""
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co/"
        self.timeout = 10  # 10 seconds timeout
        self.max_retries = 3
        self.retry_delay = 1  # 1 second between retries
    
    def _make_request(self, method: str, path: str, data: Optional[Dict] = None) -> Tuple[bool, Any]:
        """Make HTTP request with retry logic"""
        url = self.base_url + path
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == 'GET':
                    response = requests.get(
                        url, 
                        headers=headers, 
                        timeout=self.timeout
                    )
                elif method.upper() == 'POST':
                    response = requests.post(
                        url, 
                        headers=headers, 
                        json=data, 
                        timeout=self.timeout
                    )
                else:
                    return False, {"error": f"Unsupported method: {method}"}
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    time.sleep(retry_after)
                    continue
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get('status'):
                        return True, response_data.get('data', {})
                    else:
                        return False, response_data.get('message', 'Unknown error')
                else:
                    # Log error but don't raise
                    logger.error(f"Paystack API error {response.status_code}: {response.text}")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    
                    return False, {
                        'error': f'HTTP {response.status_code}',
                        'message': response.text[:200]
                    }
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Paystack request timeout (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return False, {'error': 'Request timeout after 3 retries'}
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"Paystack connection error (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return False, {'error': 'Connection error after 3 retries'}
                    
            except Exception as e:
                logger.exception("Unexpected Paystack error")
                return False, {'error': str(e)}
        
        return False, {'error': 'Max retries exceeded'}
    
    def verify_payment(self, ref: str, use_cache: bool = True) -> Tuple[bool, Any]:
        """
        Verify payment with Paystack
        
        Args:
            ref: Payment reference
            use_cache: Whether to cache successful verifications
            
        Returns:
            (success, data) tuple
        """
        # Check cache first
        if use_cache:
            cache_key = f'paystack_verify_{ref}'
            cached = cache.get(cache_key)
            if cached:
                logger.info(f"Returning cached verification for {ref}")
                return True, cached
        
        # Make API request
        success, data = self._make_request('GET', f'transaction/verify/{ref}')
        
        if success and use_cache:
            # Cache successful verification for 5 minutes
            cache.set(cache_key, data, 300)
        
        return success, data
    
    def initialize_transaction(
        self, 
        email: str, 
        amount: int, 
        reference: str,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, Any]:
        """
        Initialize a transaction
        
        Args:
            email: Customer email
            amount: Amount in kobo (smallest currency unit)
            reference: Unique reference
            callback_url: URL to redirect after payment
            metadata: Additional data
            
        Returns:
            (success, data) tuple
        """
        data = {
            "email": email,
            "amount": amount,
            "reference": reference,
        }
        
        if callback_url:
            data["callback_url"] = callback_url
        
        if metadata:
            data["metadata"] = metadata
        
        return self._make_request('POST', 'transaction/initialize', data)
    
    def list_banks(self, country: str = 'nigeria') -> Tuple[bool, Any]:
        """Get list of banks (cached for 24 hours)"""
        cache_key = f'paystack_banks_{country}'
        cached = cache.get(cache_key)
        
        if cached:
            return True, cached
        
        success, data = self._make_request('GET', f'bank?country={country}')
        
        if success:
            # Cache for 24 hours (banks rarely change)
            cache.set(cache_key, data, 86400)
        
        return success, data
    
    def resolve_account(self, account_number: str, bank_code: str) -> Tuple[bool, Any]:
        """Resolve bank account number"""
        return self._make_request(
            'GET', 
            f'bank/resolve?account_number={account_number}&bank_code={bank_code}'
        )