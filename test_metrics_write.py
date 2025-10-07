"""Test writing metrics to InfluxDB"""
import os
import sys
import io
from datetime import datetime
from dotenv import load_dotenv

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS

    token = os.getenv('INFLUXDB_TOKEN')
    org = "Trading"
    bucket = "Metrics"

    client = InfluxDBClient(
        url="http://localhost:8086",
        token=token,
        org=org
    )

    write_api = client.write_api(write_options=SYNCHRONOUS)

    print("=" * 60)
    print("Test Writing Metrics to InfluxDB")
    print("=" * 60)
    print()

    # Write test data
    print("📝 Writing test metric...")
    point = Point("test_metrics") \
        .tag("symbol", "TEST") \
        .field("test_value", 123.45) \
        .time(datetime.utcnow(), WritePrecision.NS)

    write_api.write(bucket=bucket, org=org, record=point)
    print("✅ Test metric written successfully!")

    print()

    # Query to verify
    print("📊 Querying data from last 1 hour...")
    query_api = client.query_api()

    query = f'''
    from(bucket: "{bucket}")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "test_metrics")
        |> limit(n: 5)
    '''

    result = query_api.query(query, org=org)

    if result:
        print("✅ Data found in InfluxDB!")
        for table in result:
            for record in table.records:
                print(f"   Time: {record.get_time()}")
                print(f"   Field: {record.get_field()}")
                print(f"   Value: {record.get_value()}")
    else:
        print("⚠️  No data returned (might be a timing issue)")

    client.close()

    print()
    print("=" * 60)
    print("✅ InfluxDB is working correctly!")
    print("Now restart your bot and data should appear in Grafana")
    print("=" * 60)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
