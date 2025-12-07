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


async def query_all_channel_names(gateway_ip: str, subnet: int, device_id: int, channels: int = 24, udp_port: int = 6000) -> Dict[str, str]:
    """Query all channel names with strict response validation.
    
    STRATEGY: Use SINGLE socket for all queries to avoid port conflicts.
    Send all queries first, then collect responses with channel validation.
    """
    import asyncio
    from tis_protocol import TISUDPClient
    
    _LOGGER.info(f"🔍 Starting channel name query for {subnet}.{device_id}")
    channel_names = {}
    received_channels = set()
    
    client = None
    try:
        # Single socket for all operations
        client = TISUDPClient(gateway_ip, udp_port)
        await client.async_connect(bind=True)  # Bind to receive
        client.sock.setblocking(False)  # Non-blocking mode
        
        # Get local IP for SMARTCLOUD header
        local_ip = get_local_ip()
        ip_bytes = bytes([int(x) for x in local_ip.split('.')])
        
        # PHASE 1: Send all queries with delays
        _LOGGER.info(f"📤 Sending queries for {channels} channels...")
        for channel in range(1, channels + 1):
            packet = TISPacket()
            packet.src_subnet = 1
            packet.src_device = 254
            packet.src_type = 0xFFFE
            packet.tgt_subnet = subnet
            packet.tgt_device = device_id
            packet.op_code = 0xF00E
            packet.additional_data = bytes([channel])  # 1-24 format
            
            tis_data = packet.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            client.send_to(full_packet, gateway_ip)
            _LOGGER.debug(f"📤 Query CH{channel}")
            
            # Small delay between queries to avoid flooding (200ms to reduce packet loss)
            await asyncio.sleep(0.2)
        
        # PHASE 2: Collect responses (up to 15 seconds total)
        _LOGGER.info(f"📥 Collecting responses...")
        timeout = 15.0
        start_time = time.time()
        last_response_time = start_time
        
        while time.time() - start_time < timeout:
            try:
                # Try to receive data
                data, addr = await asyncio.wait_for(
                    asyncio.get_event_loop().sock_recvfrom(client.sock, 1024),
                    timeout=0.3
                )
                
                last_response_time = time.time()
                
                # Parse response
                if b'SMARTCLOUD' in data:
                    idx = data.find(b'SMARTCLOUD')
                    tis_data = data[idx + 10:]
                else:
                    tis_data = data
                
                parsed = TISPacket.parse(tis_data)
                
                if parsed and parsed['op_code'] == 0xF00F:
                    if len(parsed['additional_data']) >= 1:
                        resp_channel = parsed['additional_data'][0]
                        
                        # DEBUG: Log all responses
                        _LOGGER.info(f"📨 Response OpCode 0xF00F: CH{resp_channel}, data_len={len(parsed['additional_data'])}")
                        
                        # Check if we already processed this channel
                        if resp_channel in received_channels:
                            _LOGGER.warning(f"⚠️ Duplicate response for CH{resp_channel}, ignoring")
                            continue
                        
                        if len(parsed['additional_data']) >= 2:
                            name_bytes = parsed['additional_data'][1:]
                            
                            # DEBUG: Log raw bytes
                            _LOGGER.debug(f"CH{resp_channel} raw bytes: {name_bytes.hex()}")
                            
                            # Check if undefined (0xFF pattern or empty)
                            if len(name_bytes) == 0 or name_bytes[0] == 0xFF:
                                _LOGGER.debug(f"CH{resp_channel}: undefined (0xFF)")
                                received_channels.add(resp_channel)
                            else:
                                # Decode UTF-8 name
                                try:
                                    null_idx = name_bytes.find(b'\x00')
                                    if null_idx > 0:
                                        name_bytes = name_bytes[:null_idx]
                                    
                                    channel_name = name_bytes.decode('utf-8').strip()
                                    if channel_name:
                                        channel_names[str(resp_channel)] = channel_name
                                        received_channels.add(resp_channel)
                                        _LOGGER.info(f"✅ CH{resp_channel}: '{channel_name}'")
                                    else:
                                        received_channels.add(resp_channel)
                                        
                                except Exception as decode_err:
                                    _LOGGER.warning(f"⚠️ CH{resp_channel} decode error: {decode_err}")
                                    received_channels.add(resp_channel)
                
                # If we got all channels, break early
                if len(received_channels) >= channels:
                    _LOGGER.info(f"🎉 All {channels} channels received!")
                    break
                    
            except asyncio.TimeoutError:
                # No data in this window
                # If no response for 3 seconds, stop waiting
                if time.time() - last_response_time > 3.0:
                    _LOGGER.info(f"⏱️ No response for 3s, stopping collection")
                    break
                continue
        
        # PHASE 3: Retry missing channels
        missing_channels = []
        for ch in range(1, channels + 1):
            if ch not in received_channels:
                missing_channels.append(ch)
        
        if missing_channels and len(missing_channels) <= 5:
            _LOGGER.warning(f"⚠️ Missing {len(missing_channels)} channels: {missing_channels}, retrying...")
            
            for channel in missing_channels:
                packet = TISPacket()
                packet.src_subnet = 1
                packet.src_device = 254
                packet.src_type = 0xFFFE
                packet.tgt_subnet = subnet
                packet.tgt_device = device_id
                packet.op_code = 0xF00E
                packet.additional_data = bytes([channel])
                
                tis_data = packet.build()
                full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
                
                client.send_to(full_packet, gateway_ip)
                _LOGGER.debug(f"🔄 Retry CH{channel}")
                await asyncio.sleep(0.3)
            
            # Collect retry responses
            retry_timeout = 5.0
            retry_start = time.time()
            
            while time.time() - retry_start < retry_timeout:
                try:
                    data = await asyncio.wait_for(
                        asyncio.get_event_loop().sock_recvfrom(client.sock, 1024),
                        timeout=0.5
                    )
                    data = data[0]
                    
                    if b'SMARTCLOUD' in data:
                        idx = data.find(b'SMARTCLOUD')
                        tis_data = data[idx + 10:]
                    else:
                        tis_data = data
                    
                    parsed = TISPacket.parse(tis_data)
                    
                    if parsed and parsed['op_code'] == 0xF00F:
                        if len(parsed['additional_data']) >= 1:
                            resp_channel = parsed['additional_data'][0]
                            
                            if resp_channel in missing_channels and resp_channel not in received_channels:
                                if len(parsed['additional_data']) >= 2:
                                    name_bytes = parsed['additional_data'][1:]
                                    
                                    if len(name_bytes) > 0 and name_bytes[0] != 0xFF:
                                        try:
                                            null_idx = name_bytes.find(b'\x00')
                                            if null_idx > 0:
                                                name_bytes = name_bytes[:null_idx]
                                            
                                            channel_name = name_bytes.decode('utf-8').strip()
                                            if channel_name:
                                                channel_names[str(resp_channel)] = channel_name
                                                received_channels.add(resp_channel)
                                                _LOGGER.info(f"✅ CH{resp_channel} (retry): '{channel_name}'")
                                        except:
                                            pass
                                    else:
                                        received_channels.add(resp_channel)
                
                except asyncio.TimeoutError:
                    continue
        
        _LOGGER.info(f"🎯 Query complete: {len(channel_names)}/{channels} names, {len(received_channels)} responses")
        
    except Exception as e:
        _LOGGER.error(f"❌ Channel name query error: {e}")
        
    finally:
        if client:
            try:
                client.close()
            except:
                pass
    
    return channel_names


async def query_device_initial_states(gateway_ip: str, subnet: int, device_id: int, channels: int = 24, udp_port: int = 6000) -> Dict[int, Dict[str, Any]]:
    """Query all channel states with OpCode 0x0033/0x0034.
    
    Returns dict with channel number as key:
    {
        1: {'is_on': True, 'brightness': 85, 'raw_value': 216},
        2: {'is_on': False, 'brightness': 0, 'raw_value': 0},
        ...
    }
    """
    import asyncio
    from tis_protocol import TISUDPClient
    
    _LOGGER.info(f"🔍 Querying initial states for {subnet}.{device_id}")
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        client = None
        try:
            client = TISUDPClient(gateway_ip, udp_port)
            await client.async_connect(bind=True)
            client.sock.setblocking(False)
            
            # Get local IP for SMARTCLOUD header
            local_ip = get_local_ip()
            ip_bytes = bytes([int(x) for x in local_ip.split('.')])
            
            # Build OpCode 0x0033 query (all channel states)
            packet = TISPacket()
            packet.src_subnet = 1
            packet.src_device = 254
            packet.src_type = 0xFFFE
            packet.tgt_subnet = subnet
            packet.tgt_device = device_id
            packet.op_code = 0x0033
            packet.additional_data = bytes()  # No data needed
            
            tis_data = packet.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            # Send query
            client.send_to(full_packet, gateway_ip)
            _LOGGER.debug(f"📤 Sent OpCode 0x0033 (state query)")
            
            # Wait for OpCode 0x0034 response
            response_timeout = 5.0
            start_time = time.time()
            
            while time.time() - start_time < response_timeout:
                try:
                    data, addr = await asyncio.wait_for(
                        asyncio.get_event_loop().sock_recvfrom(client.sock, 1024),
                        timeout=0.5
                    )
                    
                    # Parse response
                    if b'SMARTCLOUD' in data:
                        idx = data.find(b'SMARTCLOUD')
                        tis_data = data[idx + 10:]
                    else:
                        tis_data = data
                    
                    parsed = TISPacket.parse(tis_data)
                    
                    if parsed and parsed['op_code'] == 0x0034:
                        # Response format: additional_data[0] = channel_count, additional_data[1..24] = channel states
                        state_bytes = parsed.get('additional_data', bytes())
                        
                        # DEBUG: Log raw response
                        _LOGGER.debug(f"OpCode 0x0034 response: {state_bytes.hex()}")
                        _LOGGER.debug(f"Response length: {len(state_bytes)} bytes (expected {channels + 1})")
                        
                        # First byte is channel count, skip it
                        if len(state_bytes) >= channels + 1:
                            channel_count = state_bytes[0]
                            _LOGGER.debug(f"Channel count byte: 0x{channel_count:02X} ({channel_count})")
                            
                            states = {}
                            for ch in range(channels):
                                raw_value = state_bytes[ch + 1]  # Skip first byte (channel count)
                                
                                # Convert to state info
                                is_on = raw_value > 0
                                brightness = int((raw_value / 255.0) * 100) if raw_value > 0 else 0
                                
                                states[ch + 1] = {  # Channel 1-24
                                    'is_on': is_on,
                                    'brightness': brightness,
                                    'raw_value': raw_value
                                }
                                
                                # DEBUG: Log non-zero channels
                                if raw_value > 0:
                                    _LOGGER.debug(f"  CH{ch + 1}: ON (raw={raw_value}, brightness={brightness}%)")
                            
                            _LOGGER.info(f"✅ Got {len(states)} channel states")
                            return states
                        else:
                            _LOGGER.warning(f"⚠️ Invalid state response: {len(state_bytes)} bytes (expected {channels + 1})")
                
                except asyncio.TimeoutError:
                    continue
            
            _LOGGER.warning(f"⏱️ State query timeout, retry {retry_count + 1}/{max_retries}")
            retry_count += 1
            
        except Exception as e:
            _LOGGER.error(f"❌ State query error: {e}")
            retry_count += 1
            
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
            
            if retry_count < max_retries:
                await asyncio.sleep(1.0)
    
    _LOGGER.error(f"❌ Failed to query states after {max_retries} retries")
    return {}
