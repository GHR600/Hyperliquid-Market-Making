"""Check available InfluxDB organizations"""
import os
import sys
import io
from dotenv import load_dotenv

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()

try:
    from influxdb_client import InfluxDBClient

    token = os.getenv('INFLUXDB_TOKEN')
    client = InfluxDBClient(
        url="http://localhost:8086",
        token=token
    )

    print("=" * 60)
    print("Available InfluxDB Organizations and Buckets")
    print("=" * 60)
    print()

    # Get organizations API
    orgs_api = client.organizations_api()
    orgs = orgs_api.find_organizations()

    if orgs:
        for org in orgs:
            print(f"📁 Organization: {org.name}")
            print(f"   ID: {org.id}")

            # Get buckets for this org
            buckets_api = client.buckets_api()
            buckets = buckets_api.find_buckets(org=org.name).buckets

            if buckets:
                print(f"   📊 Buckets:")
                for bucket in buckets:
                    if not bucket.name.startswith('_'):  # Skip system buckets
                        print(f"      - {bucket.name}")
            print()

        print("=" * 60)
        print("To fix the issue, either:")
        print("1. Update metrics_logger.py to use one of these org names")
        print("2. Create a new org called 'trading' in InfluxDB")
        print("=" * 60)

    else:
        print("No organizations found!")

    client.close()

except Exception as e:
    print(f"Error: {e}")
