"""TIS Web UI - Standalone for Home Assistant Addon."""
import logging
import asyncio
import argparse
import os
import json
import socket
import time
from aiohttp import web
from discovery import discover_tis_devices, get_local_ip
from tis_protocol import TISProtocol, TISPacket

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TISWebUI:
    """Web UI for TIS Control."""

    def __init__(self, gateway_ip, udp_port):
        """Initialize."""
        self.gateway_ip = gateway_ip
        self.udp_port = udp_port
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/info', self.handle_info)
        self.app.router.add_get('/api/devices', self.handle_devices)
        self.app.router.add_post('/api/control', self.handle_control)
        self.app.router.add_post('/api/add_device', self.handle_add_device)
        self.app.router.add_post('/api/remove_device', self.handle_remove_device)
        self.app.router.add_get('/api/debug/messages', self.handle_debug_messages)
        self.app.router.add_post('/api/debug/start', self.handle_debug_start)
        self.app.router.add_post('/api/debug/stop', self.handle_debug_stop)
        self.runner = None
        self.site = None
        self.protocol = TISProtocol(gateway_ip, udp_port)
        self.debug_messages = []  # Store debug messages
        self.debug_listener = None  # UDP listener for debug mode
        self.debug_active = False  # Debug mode status

    async def start(self):
        """Start the web server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', 8888)
            await self.site.start()
            _LOGGER.info("TIS Web UI started on port 8888")
            _LOGGER.info("Open http://homeassistant.local:8888 in your browser")
        except Exception as e:
            _LOGGER.error(f"Failed to start TIS Web UI: {e}")

    async def stop(self):
        """Stop the web server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

    async def handle_index(self, request):
        """Serve the HTML page."""
        html = """
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TIS Cihaz Yöneticisi</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container { 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    background: white; 
                    padding: 30px; 
                    border-radius: 12px; 
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2); 
                }
                .container.full-width {
                    max-width: 100%;
                    margin: 0;
                    border-radius: 0;
                }
                header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #667eea;
                }
                h1 { 
                    color: #333; 
                    font-size: 32px;
                }
                .logo { font-size: 48px; }
                button { 
                    padding: 14px 28px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    border: none; 
                    border-radius: 8px; 
                    cursor: pointer; 
                    font-size: 16px; 
                    font-weight: 600;
                    transition: all 0.3s; 
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                }
                button:hover { 
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
                }
                button:active { transform: translateY(0); }
                button:disabled { 
                    background: #ccc; 
                    cursor: not-allowed; 
                    box-shadow: none;
                }
                .status { 
                    margin: 20px 0; 
                    padding: 15px; 
                    background: #e3f2fd; 
                    border-left: 4px solid #2196f3;
                    border-radius: 4px;
                    font-weight: 500;
                    color: #1976d2;
                }
                .devices-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                    margin-top: 20px;
                }
                .device-card {
                    background: #fff;
                    border: 2px solid #e0e0e0;
                    border-radius: 12px;
                    padding: 20px;
                    transition: all 0.3s;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .device-card:hover {
                    border-color: #667eea;
                    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
                    transform: translateY(-4px);
                }
                .device-card.added {
                    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
                    border: 2px solid #4CAF50;
                }
                .device-card.added .device-header {
                    position: relative;
                }
                .device-card.added .device-header::after {
                    content: '✓ Eklenmiş';
                    position: absolute;
                    top: -10px;
                    right: -10px;
                    background: #4CAF50;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                    box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
                }
                .device-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }
                .device-name {
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                }
                .device-icon {
                    font-size: 32px;
                }
                .device-info {
                    margin: 10px 0;
                    color: #666;
                    font-size: 14px;
                }
                .device-info strong {
                    color: #333;
                }
                .device-controls {
                    margin-top: 15px;
                    padding-top: 15px;
                    border-top: 1px solid #e0e0e0;
                    display: flex;
                    gap: 10px;
                }
                .btn-control {
                    flex: 1;
                    padding: 10px;
                    font-size: 14px;
                }
                .btn-on {
                    background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                }
                .btn-off {
                    background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                }
                .btn-remove {
                    background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                    border: 2px solid #d32f2f;
                }
                .btn-remove:hover {
                    background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%);
                    border-color: #b71c1c;
                    transform: translateY(-1px);
                    box-shadow: 0 6px 20px rgba(244, 67, 54, 0.4);
                }
                .empty-state {
                    text-align: center;
                    padding: 60px 20px;
                    color: #666;
                }
                .empty-state-icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                }
                .debug-panel {
                    background: #1e1e1e;
                    border: 2px solid #333;
                    border-radius: 8px;
                    padding: 15px;
                    margin-top: 20px;
                    max-height: 400px;
                    overflow-y: auto;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    color: #d4d4d4;
                }
                .debug-log {
                    margin: 8px 0;
                    padding: 10px;
                    border-left: 4px solid #4CAF50;
                    background: #2d2d2d;
                    border-radius: 4px;
                }
                .debug-log.send {
                    border-left-color: #2196F3;
                }
                .debug-log.receive {
                    border-left-color: #4CAF50;
                }
                .debug-log.error {
                    border-left-color: #f44336;
                }
                .debug-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .debug-time {
                    color: #858585;
                    font-size: 11px;
                }
                .debug-data {
                    color: #d4d4d4;
                    word-break: break-all;
                    line-height: 1.6;
                }
                .debug-data strong {
                    color: #4EC9B0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <div>
                        <div class="logo">🏠</div>
                        <h1>TIS Akıllı Ev Yöneticisi</h1>
                    </div>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <input type="text" id="gatewayInput" placeholder="Gateway IP (örn: 192.168.1.200)" 
                               style="padding: 10px; border: 2px solid #667eea; border-radius: 8px; font-size: 14px; width: 200px;">
                        <button id="scanBtn" onclick="scanDevices()">🔍 Cihazları Tara</button>
                        <button id="debugBtn" onclick="toggleDebug()" style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);">🔧 Debug Tool</button>
                    </div>
                </header>
                
                <div id="status" class="status">Hazır - Cihazları taramak için butona basın</div>
                
                <div id="debugPanel" class="debug-panel" style="display: none;">
                    <div class="debug-header">
                        <strong>📡 Network Debug Monitor</strong>
                        <button onclick="clearDebugLog()" style="padding: 5px 10px; font-size: 12px; background: #f44336;">Temizle</button>
                    </div>
                    <div id="debugLog" style="min-height: 100px;">
                        <div style="color: #858585; text-align: center; padding: 20px;">Debug modu başlatılmadı...</div>
                    </div>
                </div>
                
                <div id="devicesContainer" class="devices-grid">
                    <div class="empty-state">
                        <div class="empty-state-icon">📱</div>
                        <p>Henüz tarama yapılmadı</p>
                        <p style="font-size: 14px; margin-top: 10px;">Yukarıdaki "Cihazları Tara" butonuna basın</p>
                    </div>
                </div>
            </div>

            <script>
                let debugMode = false;
                let debugSocket = null;
                
                function toggleDebug() {
                    debugMode = !debugMode;
                    const panel = document.getElementById('debugPanel');
                    const btn = document.getElementById('debugBtn');
                    const container = document.querySelector('.container');
                    
                    if (debugMode) {
                        panel.style.display = 'block';
                        btn.innerText = '⏹️ Debug Durdur';
                        container.classList.add('full-width');
                        startDebugMonitor();
                    } else {
                        panel.style.display = 'none';
                        btn.innerText = '🔧 Debug Tool';
                        container.classList.remove('full-width');
                        stopDebugMonitor();
                    }
                }
                
                function startDebugMonitor() {
                    const log = document.getElementById('debugLog');
                    log.innerHTML = '<div style="color: #4CAF50;">✅ Debug monitör başlatıldı - Ağ dinleniyor...</div>';
                    
                    // Start backend UDP listener
                    fetch('/api/debug/start', { method: 'POST' })
                        .then(r => r.json())
                        .then(data => {
                            console.log('Debug listener started:', data.message);
                        })
                        .catch(e => console.error('Debug start error:', e));
                    
                    // Start polling for debug messages
                    debugSocket = setInterval(async () => {
                        try {
                            const response = await fetch('/api/debug/messages');
                            const messages = await response.json();
                            
                            messages.forEach(msg => {
                                addDebugLog(msg.type, msg.data, msg.timestamp);
                            });
                        } catch (e) {
                            // Ignore errors during polling
                        }
                    }, 500);  // Poll faster for real-time updates
                }
                
                function stopDebugMonitor() {
                    if (debugSocket) {
                        clearInterval(debugSocket);
                        debugSocket = null;
                    }
                    
                    // Stop backend UDP listener
                    fetch('/api/debug/stop', { method: 'POST' })
                        .then(r => r.json())
                        .then(data => {
                            console.log('Debug listener stopped:', data.message);
                        })
                        .catch(e => console.error('Debug stop error:', e));
                }
                
                function addDebugLog(type, data, timestamp) {
                    const log = document.getElementById('debugLog');
                    const time = new Date(timestamp || Date.now()).toLocaleTimeString();
                    
                    const typeClass = type === 'send' ? 'send' : type === 'receive' ? 'receive' : 'error';
                    const typeIcon = type === 'send' ? '📤' : type === 'receive' ? '📥' : '❌';
                    const typeLabel = type === 'send' ? 'GÖNDER' : type === 'receive' ? 'AL' : 'HATA';
                    
                    const logEntry = document.createElement('div');
                    logEntry.className = `debug-log ${typeClass}`;
                    logEntry.innerHTML = `
                        <div style="display: flex; justify-content: space-between;">
                            <strong>${typeIcon} ${typeLabel}</strong>
                            <span class="debug-time">${time}</span>
                        </div>
                        <div class="debug-data">${data}</div>
                    `;
                    
                    log.appendChild(logEntry);
                    log.scrollTop = log.scrollHeight;
                }
                
                function clearDebugLog() {
                    const log = document.getElementById('debugLog');
                    log.innerHTML = '<div style="color: #858585; text-align: center; padding: 20px;">Log temizlendi...</div>';
                }
                
                async function scanDevices() {
                    const btn = document.getElementById('scanBtn');
                    const status = document.getElementById('status');
                    const container = document.getElementById('devicesContainer');
                    const gatewayInput = document.getElementById('gatewayInput');
                    
                    btn.disabled = true;
                    btn.innerText = "⏳ Taranıyor...";
                    status.innerText = "Ağ taranıyor, lütfen bekleyin...";
                    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⏳</div><p>Ağ taranıyor...</p></div>';
                    
                    try {
                        const response = await fetch('/api/devices?gateway=' + encodeURIComponent(gatewayInput.value));
                        const devices = await response.json();
                        
                        status.innerText = `✅ Tarama tamamlandı: ${devices.length} cihaz bulundu`;
                        
                        if (devices.length === 0) {
                            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">❌</div><p>Hiç cihaz bulunamadı</p></div>';
                        } else {
                            container.innerHTML = '';
                            devices.forEach(dev => {
                                const card = createDeviceCard(dev);
                                container.innerHTML += card;
                            });
                        }
                    } catch (e) {
                        status.innerText = "❌ Hata: " + e.message;
                        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>Hata oluştu: ${e.message}</p></div>`;
                    } finally {
                        btn.disabled = false;
                        btn.innerText = "🔍 Cihazları Tara";
                    }
                }

                function createDeviceCard(dev) {
                    const icon = getDeviceIcon(dev.model_name);
                    const addedClass = dev.is_added ? 'added' : '';
                    
                    // Eklenmiş cihazlar için Sil butonu, eklenmemişler için Ekle butonu
                    let actionButton = '';
                    if (dev.is_added) {
                        actionButton = `
                            <button class="btn-control btn-remove" 
                                    onclick="removeDevice(${dev.subnet}, ${dev.device}, '${dev.name}')">
                                🗑️ Sil
                            </button>
                        `;
                    } else {
                        actionButton = `
                            <button class="btn-control" 
                                    style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);"
                                    onclick="addDevice(${dev.subnet}, ${dev.device}, '${dev.model_name}', ${dev.channels}, '${dev.name}')">
                                ➕ Ekle
                            </button>
                        `;
                    }
                    
                    return `
                        <div class="device-card ${addedClass}">
                            <div class="device-header">
                                <div class="device-name">${dev.name}</div>
                                <div class="device-icon">${icon}</div>
                            </div>
                            <div class="device-info">
                                <strong>IP:</strong> ${dev.host}<br>
                                <strong>Model:</strong> ${dev.model_name}<br>
                                <strong>Subnet/Device:</strong> ${dev.subnet}/${dev.device}<br>
                                <strong>Kanallar:</strong> ${dev.channels}
                            </div>
                            <div class="device-controls">
                                <button class="btn-control btn-on" onclick="controlDevice(${dev.subnet}, ${dev.device}, 1, 0)">
                                    💡 Aç
                                </button>
                                <button class="btn-control btn-off" onclick="controlDevice(${dev.subnet}, ${dev.device}, 0, 0)">
                                    🌙 Kapat
                                </button>
                                ${actionButton}
                            </div>
                        </div>
                    `;
                }

                function getDeviceIcon(modelName) {
                    const model = modelName.toLowerCase();
                    if (model.includes('dimmer') || model.includes('led')) return '💡';
                    if (model.includes('rgb')) return '🌈';
                    if (model.includes('curtain') || model.includes('perde')) return '🪟';
                    if (model.includes('thermo')) return '🌡️';
                    if (model.includes('sensor')) return '📡';
                    if (model.includes('relay') || model.includes('röle')) return '🔌';
                    return '📱';
                }

                async function controlDevice(subnet, deviceId, state, channel) {
                    try {
                        const response = await fetch('/api/control', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                subnet: subnet,
                                device_id: deviceId,
                                state: state,
                                channel: channel
                            })
                        });
                        
                        const result = await response.json();
                        if (result.success) {
                            document.getElementById('status').innerText = `✅ Komut gönderildi: Subnet ${subnet}, Device ${deviceId}`;
                        } else {
                            alert('Hata: ' + result.message);
                        }
                    } catch (err) {
                        alert('Hata: ' + err.message);
                    }
                }

                async function addDevice(subnet, deviceId, modelName, channels, deviceName) {
                    if (!confirm(`Cihazı Home Assistant'a eklemek istiyor musunuz?\\n\\n${deviceName}`)) {
                        return;
                    }

                    try {
                        const response = await fetch('/api/add_device', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                subnet: subnet,
                                device_id: deviceId,
                                model_name: modelName,
                                channels: channels,
                                device_name: deviceName
                            })
                        });
                        
                        const result = await response.json();
                        if (result.success) {
                            alert('✅ Cihaz başarıyla eklendi!\\n\\n' + result.message);
                            document.getElementById('status').innerText = '✅ ' + result.message;
                        } else {
                            alert('❌ Hata: ' + result.message);
                        }
                    } catch (err) {
                        alert('❌ Hata: ' + err.message);
                    }
                }

                async function removeDevice(subnet, deviceId, deviceName) {
                    if (!confirm(`"${deviceName}" cihazını silmek istediğinizden emin misiniz?\\n\\nBu işlem cihazı Home Assistant'tan tamamen kaldıracaktır.`)) {
                        return;
                    }
                    
                    try {
                        const response = await fetch('/api/remove_device', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                subnet: subnet,
                                device_id: deviceId
                            })
                        });
                        
                        const result = await response.json();
                        if (result.success) {
                            alert('✅ Cihaz başarıyla silindi!\\n\\n' + result.message);
                            document.getElementById('status').innerText = '✅ ' + result.message;
                            // Cihaz listesini yeniden tara
                            await scanDevices();
                        } else {
                            alert('❌ Hata: ' + result.message);
                        }
                    } catch (err) {
                        alert('❌ Hata: ' + err.message);
                    }
                }
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def handle_info(self, request):
        """Handle info request."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ha_ip = s.getsockname()[0]
            s.close()
        except:
            ha_ip = "unknown"
        
        return web.json_response({
            'gateway_ip': self.gateway_ip,
            'udp_port': self.udp_port,
            'ha_ip': ha_ip
        })

    async def handle_devices(self, request):
        """Handle device list request."""
        # Get gateway from query parameter or use default
        gateway_ip = request.query.get('gateway', self.gateway_ip)
        
        # Add debug log for discovery start
        self.debug_messages.append({
            'type': 'send',
            'data': f'Discovery başlatıldı - Gateway: {gateway_ip}, Port: {self.udp_port}',
            'timestamp': asyncio.get_event_loop().time() * 1000
        })
        
        devices = await discover_tis_devices(gateway_ip, self.udp_port)
        
        # Add debug log for discovery result
        self.debug_messages.append({
            'type': 'receive',
            'data': f'Discovery tamamlandı - {len(devices)} cihaz bulundu',
            'timestamp': asyncio.get_event_loop().time() * 1000
        })
        
        # Load already added devices from JSON
        import json
        added_devices = set()
        try:
            with open('/config/tis_devices.json', 'r') as f:
                existing_devices = json.load(f)
                # Extract unique_ids: tis_{subnet}_{device_id}
                added_devices = set(existing_devices.keys())
                _LOGGER.info(f"Found {len(added_devices)} already added devices")
        except FileNotFoundError:
            _LOGGER.info("No existing devices found")
        except Exception as e:
            _LOGGER.warning(f"Error reading existing devices: {e}")
        
        # Mark devices as already added
        devices_list = []
        for device in devices.values():
            subnet = device.get('subnet')
            device_id = device.get('device')  # Discovery returns 'device', not 'device_id'
            unique_id = f"tis_{subnet}_{device_id}"
            
            # Add 'is_added' flag
            device['is_added'] = unique_id in added_devices
            _LOGGER.debug(f"Device {unique_id}: is_added={device['is_added']}")
            devices_list.append(device)
        
        return web.json_response(devices_list)

    async def handle_control(self, request):
        """Handle device control request."""
        try:
            data = await request.json()
            subnet = data.get('subnet')
            device_id = data.get('device_id')
            state = data.get('state')
            channel = data.get('channel', 0)

            if subnet is None or device_id is None or state is None:
                return web.json_response({'success': False, 'message': 'Eksik parametreler'}, status=400)

            # Add debug log
            self.debug_messages.append({
                'type': 'send',
                'data': f'Kontrol komutu - Subnet: {subnet}, Device: {device_id}, State: {state}, Channel: {channel}',
                'timestamp': asyncio.get_event_loop().time() * 1000
            })

            # Send control command
            await self.protocol.send_control_command(subnet, device_id, channel, state)
            
            # Add debug log
            self.debug_messages.append({
                'type': 'receive',
                'data': f'Komut gönderildi - Yanıt bekleniyor...',
                'timestamp': asyncio.get_event_loop().time() * 1000
            })
            
            return web.json_response({'success': True})
        except Exception as e:
            _LOGGER.error(f"Control error: {e}")
            return web.json_response({'success': False, 'message': str(e)}, status=500)

    async def handle_debug_messages(self, request):
        """Handle debug messages request."""
        try:
            # Return and clear messages
            messages = self.debug_messages.copy()
            self.debug_messages.clear()
            return web.json_response(messages)
        except Exception as e:
            _LOGGER.error(f"Debug messages error: {e}")
            return web.json_response([], status=500)
    
    async def handle_debug_start(self, request):
        """Start debug UDP listener."""
        try:
            if not self.debug_active:
                self.debug_active = True
                self.debug_listener = asyncio.create_task(self._udp_debug_listener())
                _LOGGER.info("Debug UDP listener started")
                return web.json_response({'success': True, 'message': 'Debug mode başlatıldı'})
            return web.json_response({'success': True, 'message': 'Debug mode zaten aktif'})
        except Exception as e:
            _LOGGER.error(f"Debug start error: {e}")
            return web.json_response({'success': False, 'message': str(e)}, status=500)
    
    async def handle_debug_stop(self, request):
        """Stop debug UDP listener."""
        try:
            if self.debug_active:
                self.debug_active = False
                if self.debug_listener:
                    self.debug_listener.cancel()
                    self.debug_listener = None
                _LOGGER.info("Debug UDP listener stopped")
                return web.json_response({'success': True, 'message': 'Debug mode durduruldu'})
            return web.json_response({'success': True, 'message': 'Debug mode zaten pasif'})
        except Exception as e:
            _LOGGER.error(f"Debug stop error: {e}")
            return web.json_response({'success': False, 'message': str(e)}, status=500)
    
    async def _udp_debug_listener(self):
        """Listen to UDP packets for debug."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setblocking(False)
        sock.bind(('', self.udp_port))
        
        _LOGGER.info(f"Debug listener bound to port {self.udp_port}")
        
        try:
            while self.debug_active:
                try:
                    # Non-blocking receive with timeout
                    await asyncio.sleep(0.1)
                    
                    try:
                        data, addr = sock.recvfrom(4096)
                        
                        # Parse packet info
                        packet_info = self._parse_packet_for_debug(data, addr)
                        
                        self.debug_messages.append({
                            'type': 'receive',
                            'data': packet_info,
                            'timestamp': time.time() * 1000
                        })
                        
                        # Keep only last 50 messages
                        if len(self.debug_messages) > 50:
                            self.debug_messages = self.debug_messages[-50:]
                            
                    except BlockingIOError:
                        pass
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    _LOGGER.error(f"Debug listener error: {e}")
        finally:
            sock.close()
            _LOGGER.info("Debug listener closed")
    
    def _parse_packet_for_debug(self, data, addr):
        """Parse packet data for debug display."""
        try:
            ip, port = addr
            
            # Check for SMARTCLOUD header
            has_smartcloud = False
            if len(data) > 14 and data[4:14] == b'SMARTCLOUD':
                has_smartcloud = True
                source_ip_bytes = data[0:4]
                source_ip = '.'.join(str(b) for b in source_ip_bytes)
                tis_data = data[14:]
            else:
                source_ip = ip
                tis_data = data
            
            # Try to parse TIS packet
            parsed = TISPacket.parse(tis_data)
            
            if parsed:
                op_code = parsed.get('op_code', 0)
                src_subnet = parsed.get('src_subnet', 0)
                src_device = parsed.get('src_device', 0)
                tgt_subnet = parsed.get('tgt_subnet', 0)
                tgt_device = parsed.get('tgt_device', 0)
                
                # Get device name from const.py
                from const import get_device_info
                src_type = parsed.get('src_type', 0)
                model_name, channels = get_device_info(src_type)
                
                # Decode OpCode meaning
                op_meaning = self._decode_opcode(op_code, parsed)
                
                # Build detailed info
                info = f"📦 {ip}:{port}"
                if has_smartcloud:
                    info += f" (SMARTCLOUD: {source_ip})"
                info += f"<br>"
                info += f"<strong>OpCode:</strong> 0x{op_code:04X} ({op_meaning})<br>"
                info += f"<strong>Kaynak:</strong> {model_name} ({src_subnet}.{src_device})<br>"
                if tgt_subnet != 255:
                    info += f"<strong>Hedef:</strong> {tgt_subnet}.{tgt_device}<br>"
                
                # Add specific data based on OpCode
                extra_info = self._decode_packet_data(op_code, parsed)
                if extra_info:
                    info += extra_info
                
                # Add hex dump
                hex_dump = ' '.join(f'{b:02X}' for b in tis_data[:32])
                if len(tis_data) > 32:
                    hex_dump += '...'
                info += f"<div style='color:#858585; font-size:10px; margin-top:5px;'>{hex_dump}</div>"
                
                return info
            else:
                hex_dump = ' '.join(f'{b:02X}' for b in data[:32])
                if len(data) > 32:
                    hex_dump += '...'
                return f"📦 {ip}:{port} | <span style='color:#f44336;'>Parse hatası</span><br>Size: {len(data)} bytes<br><div style='color:#858585;'>{hex_dump}</div>"
                
        except Exception as e:
            return f"📦 {addr[0]}:{addr[1]} | <span style='color:#f44336;'>Hata: {str(e)}</span>"
    
    def _decode_opcode(self, op_code, parsed):
        """Decode OpCode to human readable format."""
        opcode_map = {
            0x0031: "Tek Kanal Işık Kontrolü",
            0x0032: "Tek Kanal Işık Geri Bildirimi",
            0x0034: "Multi Kanal Durum",
            0x2011: "Sensör Verileri",
            0xEFFF: "Cihaz Durumu Sorgusu",
            0xDA44: "Gateway Durumu",
            0xF003: "Cihaz Keşif (Discovery Request)",
            0xF004: "Cihaz Keşif Yanıtı (Discovery Response)",
            0x0011: "Röle Kontrolü",
            0x0012: "Röle Geri Bildirimi",
            0x0021: "Dimmer Kontrolü",
            0x0022: "Dimmer Geri Bildirimi",
            0x0041: "RGB Kontrolü",
            0x0042: "RGB Geri Bildirimi",
        }
        return opcode_map.get(op_code, f"Bilinmeyen OpCode")
    
    def _decode_packet_data(self, op_code, parsed):
        """Decode packet specific data."""
        try:
            info = ""
            additional_data = parsed.get('additional_data', b'')
            
            if op_code == 0x0031:  # Single Channel Light Control
                if len(additional_data) >= 4:
                    channel = additional_data[0]
                    state = additional_data[1]
                    info += f"<strong>Kanal:</strong> {channel} | <strong>Durum:</strong> {'Açık' if state else 'Kapalı'}<br>"
            
            elif op_code == 0x0032:  # Single Channel Light Feedback
                if len(additional_data) >= 3:
                    channel = additional_data[0]
                    # Index 1 is always 0xF8 (max brightness constant)
                    # Index 2 is actual brightness (0-248)
                    brightness_raw = additional_data[2]
                    # TIS uses 0-248 scale for 0-100%
                    brightness_pct = int((brightness_raw / 248.0) * 100)
                    info += f"<strong>Kanal:</strong> {channel} | <strong>Parlaklık:</strong> {brightness_pct}% (raw: {brightness_raw})<br>"
            
            elif op_code == 0x0034:  # Multi Channel Status
                if len(additional_data) >= 18:
                    info += "<strong>Çoklu Kanal Durumu:</strong><br>"
                    for i in range(min(8, len(additional_data))):
                        if additional_data[i] > 0:
                            brightness_pct = int((additional_data[i] / 248.0) * 100)
                            info += f"  CH{i}: {brightness_pct}% "
                    info += "<br>"
            
            elif op_code == 0x2011:  # Sensor Data
                info += "<strong>Sensör Verileri</strong> (Sıcaklık, Nem, vs.)<br>"
            
            elif op_code == 0xF003:
                info += "<strong>Ağ taraması başlatıldı</strong><br>"
            
            elif op_code == 0xF004:
                src_type = parsed.get('src_type', 0)
                info += f"<strong>Cihaz Tipi ID:</strong> 0x{src_type:04X}<br>"
            
            return info
            
        except Exception as e:
            return f"<span style='color:#f44336;'>Data decode hatası: {e}</span><br>"

    async def handle_add_device(self, request):
        """Handle add device to Home Assistant request."""
        try:
            data = await request.json()
            subnet = data.get('subnet')
            device_id = data.get('device_id')
            model_name = data.get('model_name')
            channels = data.get('channels', 1)
            device_name = data.get('device_name')

            if not all([subnet, device_id, model_name]):
                return web.json_response({'success': False, 'message': 'Eksik parametreler'}, status=400)

            # Save device to JSON file for TIS integration to read
            import json
            
            unique_id = f"tis_{subnet}_{device_id}"
            
            device_info = {
                'subnet': subnet,
                'device_id': device_id,
                'model_name': model_name,
                'channels': channels,
                'name': device_name or f"{model_name} ({subnet}.{device_id})"
            }
            
            # Save to /config/tis_devices.json (TIS integration reads from here)
            devices_file = '/config/tis_devices.json'
            devices = {}
            try:
                with open(devices_file, 'r') as f:
                    devices = json.load(f)
            except FileNotFoundError:
                _LOGGER.info("Creating new tis_devices.json file")
            except Exception as e:
                _LOGGER.warning(f"Could not read existing devices: {e}")
            
            devices[unique_id] = device_info
            
            with open(devices_file, 'w') as f:
                json.dump(devices, f, indent=2)
            
            _LOGGER.info(f"Device saved to JSON: {unique_id} - {device_name}")
            
            # Try to reload TIS integration automatically
            reload_success = await self._reload_tis_integration()
            
            if reload_success:
                return web.json_response({
                    'success': True,
                    'message': f'✅ Cihaz eklendi: {device_name}\n\n🔄 TIS entegrasyonu otomatik olarak yenilendi!\nSensörler şimdi kullanıma hazır.'
                })
            else:
                return web.json_response({
                    'success': True,
                    'message': f'✅ Cihaz eklendi: {device_name}\n\n⚠️ Sensörleri görmek için TIS entegrasyonunu manuel yenileyin:\nSettings → Integrations → TIS → ⋮ → Reload'
                })
                
        except Exception as e:
            _LOGGER.error(f"Add device error: {e}")
            return web.json_response({'success': False, 'message': f'❌ Hata: {str(e)}'}, status=500)
    
    async def handle_remove_device(self, request):
        """Handle remove device from Home Assistant request."""
        try:
            data = await request.json()
            subnet = data.get('subnet')
            device_id = data.get('device_id')

            if subnet is None or device_id is None:
                return web.json_response({'success': False, 'message': 'Eksik parametreler'}, status=400)

            unique_id = f"tis_{subnet}_{device_id}"
            
            # Remove from /config/tis_devices.json
            devices_file = '/config/tis_devices.json'
            devices = {}
            try:
                with open(devices_file, 'r') as f:
                    devices = json.load(f)
            except FileNotFoundError:
                return web.json_response({'success': False, 'message': 'Cihaz dosyası bulunamadı'}, status=404)
            
            if unique_id not in devices:
                return web.json_response({'success': False, 'message': 'Cihaz bulunamadı'}, status=404)
            
            device_name = devices[unique_id].get('name', f'{subnet}.{device_id}')
            del devices[unique_id]
            
            with open(devices_file, 'w') as f:
                json.dump(devices, f, indent=2)
            
            _LOGGER.info(f"Device removed from JSON: {unique_id} - {device_name}")
            
            # Try to reload TIS integration automatically
            reload_success = await self._reload_tis_integration()
            
            if reload_success:
                return web.json_response({
                    'success': True,
                    'message': f'🗑️ Cihaz silindi: {device_name}\n\n🔄 TIS entegrasyonu otomatik olarak yenilendi!\nCihaz Home Assistant\'tan kaldırıldı.'
                })
            else:
                return web.json_response({
                    'success': True,
                    'message': f'🗑️ Cihaz silindi: {device_name}\n\n⚠️ Home Assistant\'tan kaldırmak için TIS entegrasyonunu manuel yenileyin:\nSettings → Integrations → TIS → ⋮ → Reload'
                })
                
        except Exception as e:
            _LOGGER.error(f"Remove device error: {e}")
            return web.json_response({'success': False, 'message': f'❌ Hata: {str(e)}'}, status=500)
    
    async def _reload_tis_integration(self):
        """Reload TIS integration via Home Assistant WebSocket API."""
        try:
            import aiohttp
            import asyncio
            
            # Get supervisor token
            supervisor_token = os.environ.get('SUPERVISOR_TOKEN')
            if not supervisor_token:
                _LOGGER.warning("No SUPERVISOR_TOKEN, cannot auto-reload integration")
                return False
            
            # Use Home Assistant REST API
            base_url = "http://supervisor/core/api"
            headers = {
                "Authorization": f"Bearer {supervisor_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # First, get all config entries to find TIS entry
                list_url = f"{base_url}/config/config_entries/entry"
                
                _LOGGER.info("Getting config entries from Home Assistant...")
                async with session.get(list_url, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error(f"Failed to get config entries: HTTP {resp.status}")
                        text = await resp.text()
                        _LOGGER.error(f"Response: {text}")
                        return False
                    
                    data = await resp.json()
                    entries = data if isinstance(data, list) else []
                    
                    # Find TIS integration entry
                    tis_entry_id = None
                    for entry in entries:
                        if entry.get('domain') == 'tis':
                            tis_entry_id = entry.get('entry_id')
                            _LOGGER.info(f"Found TIS integration with entry_id: {tis_entry_id}")
                            break
                    
                    if not tis_entry_id:
                        _LOGGER.warning("TIS integration not found in config entries")
                        _LOGGER.info("Available domains: " + ", ".join([e.get('domain', 'unknown') for e in entries]))
                        return False
                    
                    # Reload the specific entry
                    reload_url = f"{base_url}/config/config_entries/entry/{tis_entry_id}/reload"
                    _LOGGER.info(f"Reloading TIS integration: {reload_url}")
                    
                    async with session.post(reload_url, headers=headers) as reload_resp:
                        if reload_resp.status == 200:
                            _LOGGER.info("✅ TIS integration reloaded successfully!")
                            return True
                        else:
                            _LOGGER.error(f"Failed to reload TIS integration: HTTP {reload_resp.status}")
                            text = await reload_resp.text()
                            _LOGGER.error(f"Response: {text}")
                            return False
                        
        except Exception as e:
            _LOGGER.error(f"Error reloading TIS integration: {e}", exc_info=True)
            return False


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='TIS Web UI Server')
    parser.add_argument('--gateway', default='192.168.1.200', help='TIS Gateway IP')
    parser.add_argument('--port', type=int, default=6000, help='UDP Port')
    args = parser.parse_args()

    web_ui = TISWebUI(args.gateway, args.port)
    await web_ui.start()
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        _LOGGER.info("Shutting down...")
        await web_ui.stop()


if __name__ == '__main__':
    asyncio.run(main())
