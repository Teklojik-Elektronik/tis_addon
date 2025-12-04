"""TIS Web UI - Standalone for Home Assistant Addon."""
import logging
import asyncio
import argparse
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
        self.app.router.add_get('/api/devices', self.handle_devices)
        self.app.router.add_post('/api/control', self.handle_control)
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
                    <button id="scanBtn" onclick="scanDevices()">🔍 Cihazları Tara</button>
                </header>
                
                <div id="status" class="status">Hazır - Cihazları taramak için butona basın</div>
                
                <div id="devicesContainer" class="devices-grid">
                    <div class="empty-state">
                        <div class="empty-state-icon">📱</div>
                        <p>Henüz tarama yapılmadı</p>
                        <p style="font-size: 14px; margin-top: 10px;">Yukarıdaki "Cihazları Tara" butonuna basın</p>
                    </div>
                </div>
            </div>

            <script>
                async function scanDevices() {
                    const btn = document.getElementById('scanBtn');
                    const status = document.getElementById('status');
                    const container = document.getElementById('devicesContainer');
                    
                    btn.disabled = true;
                    btn.innerText = "⏳ Taranıyor...";
                    status.innerText = "Ağ taranıyor, lütfen bekleyin...";
                    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⏳</div><p>Ağ taranıyor...</p></div>';
                    
                    try {
                        const response = await fetch('/api/devices');
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

                // Auto-refresh every 30 seconds
                setInterval(() => {
                    const btn = document.getElementById('scanBtn');
                    if (!btn.disabled) {
                        scanDevices();
                    }
                }, 30000);
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def handle_devices(self, request):
        """Handle device list request."""
        devices = await discover_tis_devices(self.gateway_ip, self.udp_port)
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
