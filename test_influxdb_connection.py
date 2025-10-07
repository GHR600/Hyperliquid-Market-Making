"""Quick test to verify InfluxDB connection"""
import os
import sys
import io
from dotenv import load_dotenv

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load .env file
load_dotenv()

print("=" * 60)
print("InfluxDB Connection Test")
print("=" * 60)
print()

# Check if token is loaded
token = os.getenv('INFLUXDB_TOKEN')
if token:
    print(f"✅ INFLUXDB_TOKEN loaded from .env")
    print(f"   Token length: {len(token)} characters")
    print(f"   Token preview: {token[:20]}...")
else:
    print("❌ INFLUXDB_TOKEN not found!")
    print("   Check your .env file")
    exit(1)

print()

# Try to connect to InfluxDB
try:
    from influxdb_client import InfluxDBClient

    client = InfluxDBClient(
        url="http://localhost:8086",
        token=token,
        org="trading"
    )

    # Test connection
    health = client.health()

    if health.status == "pass":
        print("✅ Successfully connected to InfluxDB!")
        print(f"   Status: {health.status}")
        print(f"   Message: {health.message}")

        # Try to query the bucket
        query_api = client.query_api()

        # Check if bucket exists
        print()
        print("📊 Checking for data in 'metrics' bucket...")

        # Simple query to see if any data exists
        query = '''
        from(bucket: "metrics")
            |> range(start: -24h)
            |> limit(n: 1)
        '''

        result = query_api.query(query, org="trading")

        if result:
            print("✅ Found data in InfluxDB!")
            for table in result:
                for record in table.records:
                    print(f"   Measurement: {record.get_measurement()}")
                    print(f"   Time: {record.get_time()}")
                    break
        else:
            print("⚠️  No data found in InfluxDB yet")
            print("   This is normal if bot hasn't run yet")

        client.close()

    else:
        print(f"⚠️  InfluxDB health check failed")
        print(f"   Status: {health.status}")
        print(f"   Message: {health.message}")

except Exception as e:
    print(f"❌ Error connecting to InfluxDB:")
    print(f"   {e}")
    print()
    print("Common issues:")
    print("1. InfluxDB not running - Start it with start_dashboard.bat")
    print("2. Wrong token - Check your InfluxDB admin panel")
    print("3. Wrong org/bucket name")

print()
print("=" * 60)
