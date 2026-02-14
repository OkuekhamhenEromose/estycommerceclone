import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
db_url = os.getenv('DATABASE_URL')
print(f"Database URL: {db_url.replace(db_url.split('@')[0].split(':')[-1], '****')}")

try:
    # Parse the URL manually
    # postgresql://user:password@host:port/dbname
    if db_url.startswith('postgresql://'):
        # Remove protocol
        rest = db_url[13:]  # len('postgresql://') = 13
        user_pass, host_port_db = rest.split('@')
        user, password = user_pass.split(':')
        host_port, dbname = host_port_db.split('/')
        
        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host = host_port
            port = 5432
        
        print(f"Connecting to: {host}:{port} as {user}")
        
        # Connect
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )
        
        # Test query
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Connected successfully!")
        print(f"PostgreSQL version: {version[0]}")
        
        cur.close()
        conn.close()
        
except Exception as e:
    print(f"❌ Connection failed: {e}")