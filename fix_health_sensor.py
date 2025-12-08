#!/usr/bin/env python3
"""Fix TIS-HEALTH-CM entity_type in devices JSON."""

import json
import sys

# Path to devices file
DEVICES_FILE = "/config/tis_devices.json"

try:
    # Load devices
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    
    print(f"Loaded {len(devices)} devices")
    
    # Find and fix TIS-HEALTH-CM devices
    fixed_count = 0
    for device_id, device_data in devices.items():
        model = device_data.get('model_name', '')
        entity_type = device_data.get('entity_type', '')
        
        if 'HEALTH' in model.upper() and entity_type == 'binary_sensor':
            print(f"Fixing {device_id}: {model} - changing entity_type from 'binary_sensor' to 'sensor'")
            device_data['entity_type'] = 'sensor'
            fixed_count += 1
    
    if fixed_count > 0:
        # Save back
        with open(DEVICES_FILE, 'w') as f:
            json.dump(devices, f, indent=2, ensure_ascii=False)
        print(f"✅ Fixed {fixed_count} devices, saved to {DEVICES_FILE}")
    else:
        print("No devices needed fixing")
    
    sys.exit(0)

except FileNotFoundError:
    print(f"❌ File not found: {DEVICES_FILE}")
    print("This script should run inside Home Assistant addon container")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
