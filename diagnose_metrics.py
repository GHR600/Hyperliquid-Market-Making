"""
Comprehensive diagnostics for InfluxDB + Grafana metrics pipeline
Run this to identify where data flow is breaking
"""
import os
import sys
import io
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 70)
print("🔍 METRICS PIPELINE DIAGNOSTICS")
print("=" * 70)
print()

# Step 1: Check environment variable
print("1️⃣  Checking INFLUXDB_TOKEN environment variable...")
token = os.environ.get('INFLUXDB_TOKEN')
if token:
    print(f"   ✅ Token found: {token[:20]}... (length: {len(token)})")
else:
    print(f"   ❌ INFLUXDB_TOKEN not set!")
    print(f"   Set it with: $env:INFLUXDB_TOKEN='your-token-here'")
    sys.exit(1)

print()

# Step 2: Check InfluxDB packages
print("2️⃣  Checking Python packages...")
try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
    print("   ✅ influxdb-client package installed")
except ImportError as e:
    print(f"   ❌ influxdb-client not installed: {e}")
    print(f"   Install with: pip install influxdb-client")
    sys.exit(1)

print()

# Step 3: Test InfluxDB connection
print("3️⃣  Testing InfluxDB connection...")
url = "http://localhost:8086"
org = "Trading"  # Must match exactly (case-sensitive)
bucket = "Metrics"  # Must match exactly (case-sensitive)

try:
    client = InfluxDBClient(url=url, token=token, org=org)
    health = client.health()
    
    if health.status == "pass":
        print(f"   ✅ InfluxDB is healthy: {health.message}")
    else:
        print(f"   ⚠️  InfluxDB health check warning: {health.status} - {health.message}")
except Exception as e:
    print(f"   ❌ Cannot connect to InfluxDB: {e}")
    print(f"   Make sure InfluxDB is running at {url}")
    sys.exit(1)

print()

# Step 4: Check organization exists
print("4️⃣  Checking organization...")
try:
    orgs_api = client.organizations_api()
    orgs = orgs_api.find_organizations()
    
    org_names = [o.name for o in orgs]
    print(f"   Available organizations: {org_names}")
    
    if org in org_names:
        print(f"   ✅ Organization '{org}' exists")
    else:
        print(f"   ❌ Organization '{org}' NOT FOUND!")
        print(f"   Either:")
        print(f"   1. Create org '{org}' in InfluxDB UI")
        print(f"   2. OR update metrics_logger.py to use: {org_names[0]}")
        sys.exit(1)
except Exception as e:
    print(f"   ⚠️  Could not list organizations: {e}")

print()

# Step 5: Check bucket exists
print("5️⃣  Checking bucket...")
try:
    buckets_api = client.buckets_api()
    buckets = buckets_api.find_buckets(org=org).buckets
    
    bucket_names = [b.name for b in buckets if not b.name.startswith('_')]
    print(f"   Available buckets: {bucket_names}")
    
    if bucket in bucket_names:
        print(f"   ✅ Bucket '{bucket}' exists")
    else:
        print(f"   ❌ Bucket '{bucket}' NOT FOUND!")
        print(f"   Either:")
        print(f"   1. Create bucket '{bucket}' in InfluxDB UI")
        print(f"   2. OR update metrics_logger.py to use: {bucket_names[0]}")
        sys.exit(1)
except Exception as e:
    print(f"   ⚠️  Could not list buckets: {e}")

print()

# Step 6: Test write to InfluxDB
print("6️⃣  Testing WRITE to InfluxDB...")
try:
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    test_point = Point("test_metrics") \
        .tag("source", "diagnostics") \
        .field("test_value", 12345.67) \
        .field("test_count", 1) \
        .time(datetime.utcnow(), WritePrecision.NS)
    
    write_api.write(bucket=bucket, org=org, record=test_point)
    print(f"   ✅ Successfully wrote test data to InfluxDB!")
    
except Exception as e:
    print(f"   ❌ Failed to write test data: {e}")
    print(f"   Check token permissions in InfluxDB UI")
    sys.exit(1)

print()

# Step 7: Test read from InfluxDB
print("7️⃣  Testing READ from InfluxDB...")
try:
    query_api = client.query_api()
    
    query = f'''
    from(bucket: "{bucket}")
        |> range(start: -10m)
        |> filter(fn: (r) => r._measurement == "test_metrics")
        |> limit(n: 1)
    '''
    
    result = query_api.query(query, org=org)
    
    if result and len(result) > 0:
        print(f"   ✅ Successfully read test data from InfluxDB!")
        for table in result:
            for record in table.records:
                print(f"      Time: {record.get_time()}")
                print(f"      Field: {record.get_field()}")
                print(f"      Value: {record.get_value()}")
    else:
        print(f"   ⚠️  No data returned from query (might be timing issue)")
        
except Exception as e:
    print(f"   ❌ Failed to read from InfluxDB: {e}")

print()

# Step 8: Check for trading_metrics data
print("8️⃣  Checking for actual trading_metrics data...")
try:
    query = f'''
    from(bucket: "{bucket}")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "trading_metrics")
        |> limit(n: 5)
    '''
    
    result = query_api.query(query, org=org)
    
    if result and len(result) > 0:
        count = sum(len(table.records) for table in result)
        print(f"   ✅ Found {count} trading_metrics records in last hour!")
        print(f"   Your bot IS writing data to InfluxDB")
        print(f"   Problem is likely in Grafana configuration")
    else:
        print(f"   ⚠️  No trading_metrics found in last hour")
        print(f"   Your bot is NOT writing data yet")
        
except Exception as e:
    print(f"   ⚠️  Could not query trading_metrics: {e}")

print()

client.close()
print("✅ Diagnostics complete!")
print("=" * 70)