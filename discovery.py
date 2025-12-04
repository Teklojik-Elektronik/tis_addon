"""Discovery helpers for TIS devices via UDP - Standalone version."""
import logging
import socket
import time
from typing import Any, Dict
from const import UDP_PORT, DISCOVERY_TIMEOUT, get_device_info
from tis_protocol import TISPacket

_LOGGER = logging.getLogger(__name__)

def get_local_ip() -> str:
    """Get local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "192.168.1.1"

DISCOVERY_OP_CODE = 0xF003
DISCOVERY_RETRIES = 10
DISCOVERY_INTERVAL = 1.5


async def discover_tis_devices(gateway_ip: str, udp_port: int = 6000) -> Dict[str, Dict[str, Any]]:
    """Discover TIS devices on the network."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_discovery, udp_port)


def _run_discovery(udp_port: int = 6000) -> Dict[str, Dict[str, Any]]:
    """Run discovery synchronously."""
    discovered = {}
    sock = None
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        except Exception:
            pass
            
        sock.settimeout(0.5)
        sock.bind(('', udp_port))
        
        # Get local IP and prepare SMARTCLOUD header
        local_ip = get_local_ip()
        ip_bytes = bytes([int(x) for x in local_ip.split('.')])
        smartcloud_header = b'SMARTCLOUD'
        
        for i in range(DISCOVERY_RETRIES):
            _LOGGER.info(f"TIS discovery broadcast {i+1}/{DISCOVERY_RETRIES}")
            
            packet = TISPacket()
            packet.op_code = DISCOVERY_OP_CODE
            packet.tgt_subnet = 255
            packet.tgt_device = 255
            tis_data = packet.build()
            
            # Add SMARTCLOUD header
            data = ip_bytes + smartcloud_header + tis_data
            
            sock.sendto(data, ('255.255.255.255', udp_port))
            
            # Listen for responses
            sub_end_time = time.time() + DISCOVERY_INTERVAL
            while time.time() < sub_end_time:
                try:
                    data, addr = sock.recvfrom(4096)
                    ip = addr[0]
                    
                    # Remove SMARTCLOUD header if present
                    if len(data) > 14 and data[4:14] == b'SMARTCLOUD':
                        data = data[14:]
                    
                    parsed = TISPacket.parse(data)
                    if parsed:
                        subnet = parsed['src_subnet']
                        device = parsed['src_device']
                        unique_id = f"tis_{subnet}_{device}"
                        
                        device_type_id = parsed['src_type']
                        model_name, channels = get_device_info(device_type_id)
                        
                        # Extract device name
                        device_name_from_packet = None
                        if parsed['op_code'] == 0x000F and parsed.get('additional_data'):
                            try:
                                raw_name = parsed['additional_data']
                                null_pos = raw_name.find(0)
                                if null_pos != -1:
                                    raw_name = raw_name[:null_pos]
                                device_name_from_packet = raw_name.decode('utf-8', errors='ignore').strip()
                            except Exception:
                                pass
                        
                        final_name = f"{model_name} ({subnet}.{device})"
                        if device_name_from_packet:
                            final_name = f"{device_name_from_packet} ({subnet}.{device})"

                        if unique_id not in discovered:
                            _LOGGER.info(f"Found: {ip} ({subnet}.{device}) - {model_name}")
                            discovered[unique_id] = {
                                "host": ip,
                                "subnet": subnet,
                                "device": device,
                                "device_type": device_type_id,
                                "device_type_hex": f"0x{device_type_id:04X}",
                                "model_name": model_name,
                                "channels": channels,
                                "name": final_name,
                            }
                        elif device_name_from_packet:
                            discovered[unique_id]["name"] = final_name
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    _LOGGER.error(f"Socket error: {e}")
        
        # Final wait
        _LOGGER.info("Waiting for final responses...")
        final_end_time = time.time() + 4.0
        while time.time() < final_end_time:
            try:
                data, addr = sock.recvfrom(4096)
                ip = addr[0]
                
                if len(data) > 14 and data[4:14] == b'SMARTCLOUD':
                    data = data[14:]
                
                parsed = TISPacket.parse(data)
                if parsed:
                    subnet = parsed['src_subnet']
                    device = parsed['src_device']
                    unique_id = f"tis_{subnet}_{device}"
                    
                    if unique_id not in discovered:
                        device_type_id = parsed['src_type']
                        model_name, channels = get_device_info(device_type_id)
                        final_name = f"{model_name} ({subnet}.{device})"
                        
                        _LOGGER.info(f"Late discovery: {ip} ({subnet}.{device}) - {model_name}")
                        discovered[unique_id] = {
                            "host": ip,
                            "subnet": subnet,
                            "device": device,
                            "device_type": device_type_id,
                            "device_type_hex": f"0x{device_type_id:04X}",
                            "model_name": model_name,
                            "channels": channels,
                            "name": final_name,
                        }
                        
            except socket.timeout:
                continue
            except Exception as e:
                _LOGGER.error(f"Final wait error: {e}")
        
    except Exception as e:
        _LOGGER.error(f"Discovery error: {e}")
    finally:
        if sock:
            sock.close()
    
    _LOGGER.info(f"Discovery complete: {len(discovered)} devices found")
    return discovered
