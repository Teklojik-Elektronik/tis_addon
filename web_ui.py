"""TIS Web UI - Standalone for Home Assistant Addon."""
import logging
import asyncio
import argparse
import os
import json
from aiohttp import web
from discovery import discover_tis_devices
from tis_protocol import TISProtocol

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
        self.runner = None
        self.site = None
        self.protocol = TISProtocol(gateway_ip, udp_port)

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
                .empty-state {
                    text-align: center;
                    padding: 60px 20px;
                    color: #666;
                }
                .empty-state-icon {
                    font-size: 64px;
                    margin-bottom: 20px;
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
                               value="{self.gateway_ip if self.gateway_ip != '0.0.0.0' else ''}" 
                               style="padding: 10px; border: 2px solid #667eea; border-radius: 8px; font-size: 14px; width: 200px;">
                        <button id="scanBtn" onclick="scanDevices()">🔍 Cihazları Tara</button>
                    </div>
                </header>
                
                <div id="status" class="status">Hazır - Cihazları taramak için butona basın</div>
                
                <div style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 15px; margin: 15px 0;">
                    <strong>🔌 Bağlantı Bilgileri:</strong><br>
                    <span style="font-size: 14px;">
                        Gateway IP: <strong id="currentGateway">{self.gateway_ip if self.gateway_ip != '0.0.0.0' else 'Yapılandırılmadı'}</strong> | 
                        UDP Port: <strong>{self.udp_port}</strong> | 
                        Home Assistant IP: <strong id="haIP">Kontrol ediliyor...</strong>
                    </span>
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
                // Get Home Assistant IP
                fetch('/api/info')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('haIP').textContent = data.ha_ip || 'N/A';
                    })
                    .catch(e => {
                        document.getElementById('haIP').textContent = 'Bilinmiyor';
                    });

                async function scanDevices() {
                    const btn = document.getElementById('scanBtn');
                    const status = document.getElementById('status');
                    const container = document.getElementById('devicesContainer');
                    const gatewayInput = document.getElementById('gatewayInput');
                    
                    // Update current gateway display
                    document.getElementById('currentGateway').textContent = gatewayInput.value;
                    
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
                    return `
                        <div class="device-card">
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
                                <button class="btn-control" style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);" 
                                        onclick="addDevice(${dev.subnet}, ${dev.device}, '${dev.model_name}', ${dev.channels}, '${dev.name}')">
                                    ➕ Ekle
                                </button>
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
        devices = await discover_tis_devices(gateway_ip, self.udp_port)
        return web.json_response(list(devices.values()))

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

            # Send control command
            await self.protocol.send_control_command(subnet, device_id, channel, state)
            
            return web.json_response({'success': True})
        except Exception as e:
            _LOGGER.error(f"Control error: {e}")
            return web.json_response({'success': False, 'message': str(e)}, status=500)

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
    
    async def _reload_tis_integration(self):
        """Reload TIS integration via Home Assistant API."""
        try:
            import aiohttp
            
            # Get supervisor token
            supervisor_token = os.environ.get('SUPERVISOR_TOKEN')
            if not supervisor_token:
                _LOGGER.warning("No SUPERVISOR_TOKEN, cannot auto-reload integration")
                return False
            
            # Call Home Assistant API to reload config entry
            url = "http://supervisor/core/api/config/config_entries/entry"
            headers = {
                "Authorization": f"Bearer {supervisor_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # First, get all config entries to find TIS entry
                list_url = "http://supervisor/core/api/config/config_entries/entry"
                async with session.get(list_url, headers=headers) as resp:
                    if resp.status == 200:
                        entries = await resp.json()
                        
                        # Find TIS integration entry
                        tis_entry_id = None
                        for entry in entries:
                            if entry.get('domain') == 'tis':
                                tis_entry_id = entry.get('entry_id')
                                break
                        
                        if not tis_entry_id:
                            _LOGGER.warning("TIS integration not found in config entries")
                            return False
                        
                        # Reload the specific entry
                        reload_url = f"http://supervisor/core/api/config/config_entries/entry/{tis_entry_id}/reload"
                        async with session.post(reload_url, headers=headers) as reload_resp:
                            if reload_resp.status == 200:
                                _LOGGER.info("TIS integration reloaded successfully")
                                return True
                            else:
                                _LOGGER.warning(f"Failed to reload TIS integration: {reload_resp.status}")
                                return False
                    else:
                        _LOGGER.warning(f"Failed to get config entries: {resp.status}")
                        return False
                        
        except Exception as e:
            _LOGGER.error(f"Error reloading TIS integration: {e}")
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
