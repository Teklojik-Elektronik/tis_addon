import struct

packets = [
    ('CRC00001', '20:25:08.377', '0C 01 28 CC B2 01 1E 01 FE 01 39 0E'),
    ('CRC00002', '20:25:08.429', '0D 01 FE 80 7A 01 1F FF FF 01 02 1A C5'),
    ('CRC00003', '20:25:12.655', '0F 01 28 CC B2 01 04 01 FE 01 06 00 00 C1 0B'),
    ('CRC00004', '20:25:12.709', '0D 01 FE 80 7A 01 05 FF FF 01 06 18 B5'),
    ('CRC00005', '20:25:13.693', '0F 01 28 CC B2 01 04 01 FE 01 06 00 00 C1 0B'),
    ('CRC00006', '20:25:13.749', '0D 01 FE 80 7A 01 05 FF FF 01 06 18 B5'),
]

opcodes = {
    0x0104: 'Device Type Query Response',
    0x0105: 'Device Type Info',
    0x011E: 'Unknown Command 0x011E',
    0x011F: 'Unknown Command 0x011F',
    0x2011: 'Sensor Data Report',
    0xDA44: 'Broadcast Notification',
}

print('=== TIS PROTOCOL - 2025-12-08 20:25 ===\n')

for crc_id, timestamp, pkt_hex in packets:
    data = bytes.fromhex(pkt_hex.replace(' ', ''))
    length = data[0]
    header = data[1:3]
    src = data[3]
    dst = data[4]
    opcode = struct.unpack('>H', data[5:7])[0]
    payload = data[7:-2]
    crc = struct.unpack('>H', data[-2:])[0]
    
    print(f'{crc_id} {timestamp}')
    print(f'  Length: {length} bytes')
    print(f'  Header: {header.hex().upper()} ({"Query" if header == bytes([0x01, 0xFE]) else "Response" if header == bytes([0x01, 0x28]) else "Other"})')
    print(f'  Source: 0x{src:02X} ({src})')
    print(f'  Dest: 0x{dst:02X} ({dst})')
    print(f'  OpCode: 0x{opcode:04X} - {opcodes.get(opcode, "Unknown")}')
    
    if len(payload) > 0:
        print(f'  Payload: {payload.hex().upper()} ({len(payload)} bytes)')
        
        # Parse specific payloads
        if opcode == 0x011E:
            if len(payload) >= 3:
                val1 = struct.unpack('>H', payload[0:2])[0]
                val2 = payload[2]
                print(f'    → Device Type: 0x{val1:04X}, Channel: {val2}')
        
        elif opcode == 0x011F:
            if len(payload) >= 3:
                val1 = struct.unpack('>H', payload[0:2])[0]
                val2 = payload[2]
                print(f'    → Response: Type=0x{val1:04X}, Channel={val2}')
        
        elif opcode == 0x0104:
            if len(payload) >= 5:
                val1 = struct.unpack('>H', payload[0:2])[0]
                val2 = payload[2]
                val3 = struct.unpack('>H', payload[3:5])[0]
                print(f'    → Device Type: 0x{val1:04X}, Channel: {val2}, Data: 0x{val3:04X}')
        
        elif opcode == 0x0105:
            if len(payload) >= 3:
                val1 = struct.unpack('>H', payload[0:2])[0]
                val2 = payload[2]
                print(f'    → Query: 0x{val1:04X}, Channel: {val2}')
    
    print(f'  CRC: 0x{crc:04X}')
    print()

# Summary
print('=== ÖZET ===')
print('CRC00001: 0x011E komutu - Yeni komut türü (0xCC→0xB2)')
print('          Header: 0128 (Response/Device-specific)')
print('          Payload: Device Type=0x01FE, Channel=1')
print()
print('CRC00002: 0x011F komutu - Yanıt paketi (0x80→0x7A)')
print('          Header: 01FE (Query/Request)')
print('          Payload: 0xFFFF 01 02')
print()
print('CRC00003-006: Standart cihaz keşif döngüsü (tekrarlı)')
print('  - CRC00003/005: 0x0104 (Device Type Query Response)')
print('    Source: 0xCC → Dest: 0xB2')
print('    Payload: Type=0x01FE, Channel=1, Data=0x0000')
print()
print('  - CRC00004/006: 0x0105 (Device Type Info)')
print('    Source: 0x80 → Dest: 0x7A')
print('    Payload: Query=0xFFFF, Channel=1')
print()
print('=== ANALİZ ===')
print('• 0x011E ve 0x011F: Yeni komut çifti (daha önce görülmemiş)')
print('• Cihaz adresleri: 0x7A (122), 0x80 (128), 0xB2 (178), 0xCC (204)')
print('• Channel değişikliği: İlk paketlerde Channel=1, sonra Channel=1,6')
print('• Tekrarlı paketler: CRC00003=CRC00005, CRC00004=CRC00006')
