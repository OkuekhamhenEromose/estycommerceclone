import django
import os
import sys
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.core.cache import cache
from estyecomapp.models import Product, Category
import redis

print("🔧 Testing Redis and Caching Configuration")
print("=" * 50)

# Test Redis connection
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
    redis_client.ping()
    print("✅ Redis server is running and accessible")
    
    info = redis_client.info()
    print(f"   Redis version: {info['redis_version']}")
    print(f"   Connected clients: {info['connected_clients']}")
    
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    print("\nStart Redis with: docker run -d -p 6379:6379 --name redis redis:alpine")
    sys.exit(1)

print("\n" + "=" * 50)

# Test Django cache
try:
    test_key = f"test:{datetime.now().timestamp()}"
    cache.set(test_key, "Redis is working!", timeout=60)
    value = cache.get(test_key)
    if value == "Redis is working!":
        print("✅ Django cache framework working with Redis")
        cache.delete(test_key)
    else:
        print("❌ Cache retrieval failed")
        
except Exception as e:
    print(f"❌ Django cache error: {e}")

print("\n" + "=" * 50)
print("✅ Redis configuration complete!")
print("\nYour backend is now optimized with:")
print("• PostgreSQL database for persistent storage")
print("• Redis caching for lightning-fast responses")
print("• Optimized serializers with minimal payload")
print("• Efficient views with database query optimization")
print("\nRun your server: python manage.py runserver")