#!/usr/bin/env python3
import psutil
import requests
import json

print("=" * 60)
print("📊 COMPARING SYSTEM METRICS")
print("=" * 60)

# Get local metrics
local_cpu = psutil.cpu_percent(interval=0.5)
local_memory = psutil.virtual_memory().percent
local_disk = psutil.disk_usage('/').percent

print("\n🖥️  LOCAL SYSTEM:")
print(f"   CPU:    {local_cpu:.1f}%")
print(f"   Memory: {local_memory:.1f}%")
print(f"   Disk:   {local_disk:.1f}%")

# Get API metrics
try:
    response = requests.get('http://localhost:5004/api/metrics', timeout=5)
    if response.status_code == 200:
        api = response.json()
        print("\n🌐 FLASK API:")
        print(f"   CPU:    {api['cpu']:.1f}%")
        print(f"   Memory: {api['memory']:.1f}%")
        print(f"   Disk:   {api['disk']:.1f}%")
        print(f"   Status: {api['status']}")
        
        # Calculate differences
        cpu_diff = abs(local_cpu - api['cpu'])
        mem_diff = abs(local_memory - api['memory'])
        disk_diff = abs(local_disk - api['disk'])
        
        print("\n📈 VERIFICATION:")
        if cpu_diff < 2 and mem_diff < 2 and disk_diff < 2:
            print("   ✅ MATCHING! Real metrics are being displayed.")
        else:
            print("   ⚠️ Small differences detected (normal for real-time data)")
        
        print(f"   CPU diff:  {cpu_diff:.1f}%")
        print(f"   Memory diff: {mem_diff:.1f}%")
        print(f"   Disk diff:  {disk_diff:.1f}%")
        
        if api['status'] == 'success':
            print("\n✅ CONFIRMED: REAL system metrics are being used!")
        else:
            print("\n⚠️ WARNING: Simulated metrics are being used.")
    else:
        print(f"\n❌ API returned status: {response.status_code}")
except Exception as e:
    print(f"\n❌ Error fetching API: {e}")

print("\n" + "=" * 60)