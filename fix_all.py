import os
import sys

print("🔧 Fixing Django PostgreSQL Connection")
print("=" * 50)

# 1. Create logs directory
logs_dir = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
    print(f"✅ Created logs directory: {logs_dir}")
else:
    print(f"✅ Logs directory already exists: {logs_dir}")

# 2. Check .env file
env_file = os.path.join(os.getcwd(), '.env')
if os.path.exists(env_file):
    print(f"✅ Found .env file")
    
    # Read and check DATABASE_URL
    with open(env_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('DATABASE_URL'):
                db_url = line.strip()
                print(f"Current DATABASE_URL: {db_url}")
                
                # Check if password contains @
                if '@' in db_url.split('@')[0].split(':')[-1]:
                    print("⚠️  Warning: Password contains '@' which needs to be URL-encoded as %40")
                    print("   Update your .env file with:")
                    print("   DATABASE_URL=postgresql://postgres:Lionsdonteatgrass7%40@localhost:5432/etsydb")
                break
else:
    print(f"❌ .env file not found at: {env_file}")

# 3. Test connection
try:
    import psycopg2
    from decouple import config
    
    db_url = config('DATABASE_URL', default='')
    if db_url:
        print(f"\nTesting connection...")
        # Parse URL (mask password)
        parts = db_url.split('@')
        user_pass = parts[0].split('://')[1].split(':')
        masked = f"{user_pass[0]}:****@{parts[1]}"
        print(f"Connecting to: {masked}")
        
        # Connect
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Successfully connected!")
        print(f"PostgreSQL version: {version[0]}")
        cur.close()
        conn.close()
    else:
        print("❌ DATABASE_URL not set")
        
except ImportError:
    print("\n📦 Installing required packages...")
    os.system('pip install psycopg2-binary python-decouple')
    print("Run this script again after installation.")
except Exception as e:
    print(f"❌ Connection failed: {e}")

print("\n" + "=" * 50)
print("Next steps:")
print("1. Ensure logs directory exists (already done)")
print("2. Update .env with URL-encoded password if needed")
print("3. Run: python test_db_connection.py")