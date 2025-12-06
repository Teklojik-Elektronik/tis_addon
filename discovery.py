"""Discovery helpers for TIS devices via UDP - Standalone version."""
import logging
import socket
import time
from typing import Any, Dict
from const import UDP_PORT, DISCOVERY_TIMEOUT, get_device_info, get_device_description
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
                        
                        # Skip unknown/system devices (Home Assistant itself)
                        if model_name == "Unknown Device" or device_type_id == 0xFFFE:
                            _LOGGER.debug(f"Skipping system device: {ip} ({subnet}.{device})")
                            continue
                        
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
                                "description": get_device_description(model_name),
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
                        
                        # Skip unknown/system devices
                        if model_name == "Unknown Device" or device_type_id == 0xFFFE:
                            continue
                        
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
                            "description": get_device_description(model_name),
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


class TISDiscovery:
    """TIS Discovery with real-time callback support."""
    
    def __init__(self, gateway_ip: str, udp_port: int = 6000):
        self.gateway_ip = gateway_ip
        self.udp_port = udp_port
    
    async def discover_with_callback(self, on_device_found):
        """Discover devices and call callback for each device found."""
        import asyncio
        loop = asyncio.get_event_loop()
        
        discovered = {}
        
        def discovery_worker():
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(0.5)
                sock.bind(('', self.udp_port))
                
                local_ip = get_local_ip()
                ip_bytes = bytes([int(x) for x in local_ip.split('.')])
                smartcloud_header = b'SMARTCLOUD'
                
                for i in range(DISCOVERY_RETRIES):
                    packet = TISPacket()
                    packet.op_code = DISCOVERY_OP_CODE
                    packet.tgt_subnet = 255
                    packet.tgt_device = 255
                    tis_data = packet.build()
                    data = ip_bytes + smartcloud_header + tis_data
                    sock.sendto(data, ('255.255.255.255', self.udp_port))
                    
                    sub_end_time = time.time() + DISCOVERY_INTERVAL
                    while time.time() < sub_end_time:
                        try:
                            data, addr = sock.recvfrom(4096)
                            ip = addr[0]
                            
                            if len(data) > 14 and data[4:14] == b'SMARTCLOUD':
                                data = data[14:]
                            
                            parsed = TISPacket.parse(data)
                            if parsed:
                                subnet = parsed['src_subnet']
                                device_id = parsed['src_device']
                                unique_id = f"tis_{subnet}_{device_id}"
                                
                                device_type_id = parsed['src_type']
                                model_name, channels = get_device_info(device_type_id)
                                
                                if model_name == "Unknown Device" or device_type_id == 0xFFFE:
                                    continue
                                
                                if unique_id not in discovered:
                                    device_info = {
                                        "host": ip,
                                        "subnet": subnet,
                                        "device": device_id,
                                        "device_type": device_type_id,
                                        "device_type_hex": f"0x{device_type_id:04X}",
                                        "model_name": model_name,
                                        "channels": channels,
                                        "name": f"{model_name} ({subnet}.{device_id})",
                                        "description": get_device_description(model_name),
                                    }
                                    discovered[unique_id] = device_info
                                    
                                    # Trigger callback immediately
                                    asyncio.run_coroutine_threadsafe(
                                        on_device_found(device_info), 
                                        loop
                                    )
                                    
                        except socket.timeout:
                            continue
                        except Exception as e:
                            _LOGGER.error(f"Socket error: {e}")
                
            except Exception as e:
                _LOGGER.error(f"Discovery error: {e}")
            finally:
                if sock:
                    sock.close()
            
            return discovered
        
        # Run in executor to not block event loop
        return await loop.run_in_executor(None, discovery_worker)


async def query_device_initial_states(gateway_ip: str, subnet: int, device_id: int, udp_port: int = 6000) -> Dict[str, Dict]:
    """Query device channel states with OpCode 0x0033, return initial states."""
    import asyncio
    from tis_protocol import TISUDPClient
    
    try:
        client = TISUDPClient(gateway_ip, udp_port)
        await client.async_connect(bind=False)
        
        # Get local IP for SMARTCLOUD header
        local_ip = get_local_ip()
        ip_bytes = bytes([int(x) for x in local_ip.split('.')])
        
        # Build OpCode 0x0033 query (multi-channel status query)
        packet = TISPacket()
        packet.src_subnet = 1
        packet.src_device = 254
        packet.src_type = 0xFFFE
        packet.tgt_subnet = subnet
        packet.tgt_device = device_id
        packet.op_code = 0x0033
        packet.additional_data = bytes([])
        
        tis_data = packet.build()
        full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
        
        # Send query
        client.send_to(full_packet, gateway_ip)
        _LOGGER.info(f"Sent OpCode 0x0033 to {subnet}.{device_id}")
        
        # Wait for response (OpCode 0x0034)
        await asyncio.sleep(0.5)
        
        try:
            data, addr = await asyncio.wait_for(
                client.sock.recvfrom(1024), 
                timeout=2.0
            )
            
            _LOGGER.debug(f"Received {len(data)} bytes from {addr}")
            
            # Parse OpCode 0x0034
            if b'SMARTCLOUD' in data:
                idx = data.find(b'SMARTCLOUD')
                tis_data = data[idx + 10:]
            else:
                tis_data = data
            
            parsed = TISPacket.parse(tis_data)
            
            if parsed and parsed['op_code'] == 0x0034:
                _LOGGER.info(f"Received OpCode 0x0034 from {parsed['src_subnet']}.{parsed['src_device']}")
                
                # Extract channel states (0-23 → channels 1-24)
                channel_states = {}
                for ch in range(1, 25):
                    idx = ch - 1
                    if idx < len(parsed['additional_data']):
                        brightness_raw = parsed['additional_data'][idx]
                        brightness_pct = int((brightness_raw / 248.0) * 100)
                        channel_states[str(ch)] = {
                            'is_on': brightness_raw > 0,
                            'brightness': brightness_pct,
                            'raw': brightness_raw
                        }
                        if brightness_raw > 0:
                            _LOGGER.debug(f"  CH{ch}: ON ({brightness_pct}%)")
                
                client.close()
                return channel_states
            else:
                _LOGGER.warning(f"Expected OpCode 0x0034, got 0x{parsed['op_code']:04X}" if parsed else "Parse failed")
        
        except asyncio.TimeoutError:
            _LOGGER.warning(f"Timeout waiting for OpCode 0x0034 from {subnet}.{device_id}")
        
        client.close()
        return {}
        
    except Exception as e:
        _LOGGER.error(f"Error querying initial states for {subnet}.{device_id}: {e}")
        return {}

