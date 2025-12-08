"""TIS Web UI - Standalone for Home Assistant Addon."""
import logging
import asyncio
import argparse
import os
import json
import socket
import time
from aiohttp import web
from discovery import discover_tis_devices, get_local_ip, query_all_channel_names, query_device_initial_states
from tis_protocol import TISProtocol, TISPacket, TISUDPClient

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
        self.app.router.add_get('/api/devices/stream', self.handle_devices_stream)
        self.app.router.add_post('/api/control', self.handle_control)
        self.app.router.add_post('/api/query_device', self.handle_query_device)
        self.app.router.add_post('/api/add_device', self.handle_add_device)
        self.app.router.add_post('/api/remove_device', self.handle_remove_device)
        self.app.router.add_post('/api/fix_entity_types', self.handle_fix_entity_types)
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
                    background: #f0f0f0;
                    min-height: 100vh;
                    padding: 0;
                    margin: 0;
                }
                .container { 
                    max-width: 100%; 
                    margin: 0; 
                    background: white; 
                    padding: 0; 
                    min-height: 100vh;
                    border-radius: 0; 
                    box-shadow: none; 
                    display: flex;
                    flex-direction: column;
                }
                .container.full-width {
                    max-width: 100%;
                    margin: 0;
                    border-radius: 0;
                }
                
                /* Menu Bar - TIS Style */
                .menubar {
                    background: #f5f5f5;
                    border-bottom: 1px solid #d0d0d0;
                    padding: 8px 15px;
                    display: flex;
                    gap: 5px;
                }
                .menubar-item {
                    padding: 6px 12px;
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: normal;
                    color: #333;
                    transition: all 0.2s;
                }
                .menubar-item:hover {
                    background: #e0e0e0;
                    border-color: #c0c0c0;
                }
                
                /* Title Bar */
                .titlebar {
                    background: white;
                    padding: 10px 15px;
                    border-bottom: 1px solid #e0e0e0;
                    font-size: 13px;
                    color: #666;
                }
                
                /* Toolbar */
                .toolbar {
                    background: #f9f9f9;
                    padding: 8px 15px;
                    border-bottom: 1px solid #e0e0e0;
                    display: flex;
                    gap: 8px;
                    align-items: center;
                }
                .toolbar button {
                    padding: 6px 16px;
                    background: #fff;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    font-size: 13px;
                    cursor: pointer;
                    transition: all 0.2s;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                }
                .toolbar button:hover {
                    background: #f0f0f0;
                    border-color: #999;
                }
                .toolbar button:active {
                    background: #e0e0e0;
                }
                .toolbar button.primary {
                    background: #4a90e2;
                    color: white;
                    border-color: #357abd;
                }
                .toolbar button.primary:hover {
                    background: #357abd;
                }
                
                /* Table Container */
                .table-container {
                    flex: 1;
                    overflow: auto;
                    background: white;
                }
                .devices-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                }
                .devices-table thead {
                    background: #f5f5f5;
                    border-bottom: 2px solid #d0d0d0;
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }
                .devices-table th {
                    padding: 10px 12px;
                    text-align: left;
                    font-weight: 600;
                    color: #333;
                    border-right: 1px solid #e0e0e0;
                    white-space: nowrap;
                }
                .devices-table th:last-child {
                    border-right: none;
                }
                .devices-table tbody tr {
                    border-bottom: 1px solid #e8e8e8;
                    transition: background 0.2s;
                }
                .devices-table tbody tr:hover {
                    background: #f9f9f9;
                }
                .devices-table tbody tr.added {
                    background: #e8f5e9;
                }
                .devices-table tbody tr.added:hover {
                    background: #d0f0d2;
                }
                .devices-table td {
                    padding: 10px 12px;
                    border-right: 1px solid #f0f0f0;
                    color: #333;
                }
                .devices-table td:last-child {
                    border-right: none;
                }
                .devices-table td.center {
                    text-align: center;
                }
                
                /* Status Indicator */
                .status-icon {
                    display: inline-block;
                    width: 16px;
                    height: 16px;
                    line-height: 16px;
                    text-align: center;
                    font-size: 12px;
                }
                .status-icon.added {
                    color: #4CAF50;
                }
                
                /* Action Buttons in Table - Laravel Backpack Style */
                .table-actions {
                    display: flex;
                    gap: 2px;
                    justify-content: flex-end;
                }
                .table-actions .btn {
                    padding: 4px 8px;
                    font-size: 11px;
                    border: 1px solid transparent;
                    border-radius: 3px;
                    cursor: pointer;
                    transition: all 0.15s ease-in-out;
                    font-weight: 500;
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    line-height: 1.5;
                    min-width: 32px;
                    text-align: center;
                    justify-content: center;
                }
                .table-actions .btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
                }
                .table-actions .btn:active {
                    transform: translateY(0);
                }
                .table-actions .btn-success {
                    background-color: #5cb85c;
                    border-color: #4cae4c;
                    color: white;
                }
                .table-actions .btn-success:hover {
                    background-color: #449d44;
                    border-color: #398439;
                }
                .table-actions .btn-danger {
                    background-color: #d9534f;
                    border-color: #d43f3a;
                    color: white;
                }
                .table-actions .btn-danger:hover {
                    background-color: #c9302c;
                    border-color: #ac2925;
                }
                .table-actions .btn-primary {
                    background-color: #337ab7;
                    border-color: #2e6da4;
                    color: white;
                }
                .table-actions .btn-primary:hover {
                    background-color: #286090;
                    border-color: #204d74;
                }
                .table-actions .btn-warning {
                    background-color: #f0ad4e;
                    border-color: #eea236;
                    color: white;
                }
                .table-actions .btn-warning:hover {
                    background-color: #ec971f;
                    border-color: #d58512;
                }
                .table-actions .btn-icon {
                    padding: 4px 6px;
                    min-width: 28px;
                }
                /* Dropdown Style Actions */
                .table-actions .dropdown {
                    position: relative;
                    display: inline-block;
                }
                .table-actions .btn-group {
                    display: inline-flex;
                    gap: 0;
                }
                .table-actions .btn-group .btn {
                    border-radius: 0;
                }
                .table-actions .btn-group .btn:first-child {
                    border-top-left-radius: 3px;
                    border-bottom-left-radius: 3px;
                }
                .table-actions .btn-group .btn:last-child {
                    border-top-right-radius: 3px;
                    border-bottom-right-radius: 3px;
                }
                
                /* Status Bar */
                .statusbar {
                    background: #f5f5f5;
                    border-top: 1px solid #d0d0d0;
                    padding: 6px 15px;
                    font-size: 12px;
                    color: #666;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 15px;
                }
                
                /* Progress Bar */
                .progress-container {
                    flex: 1;
                    max-width: 300px;
                    height: 20px;
                    background: #e0e0e0;
                    border-radius: 10px;
                    overflow: hidden;
                    position: relative;
                    display: none;
                }
                .progress-container.active {
                    display: block;
                }
                .progress-bar {
                    height: 100%;
                    background: linear-gradient(90deg, #4CAF50, #45a049);
                    transition: width 0.3s ease;
                    position: relative;
                }
                .progress-bar::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    bottom: 0;
                    right: 0;
                    background: linear-gradient(
                        90deg,
                        rgba(255, 255, 255, 0) 0%,
                        rgba(255, 255, 255, 0.3) 50%,
                        rgba(255, 255, 255, 0) 100%
                    );
                    animation: shimmer 1.5s infinite;
                }
                @keyframes shimmer {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
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
                <!-- Menu Bar -->
                <div class="menubar">
                    <button class="menubar-item">Project</button>
                    <button class="menubar-item">Configuration</button>
                    <button class="menubar-item">Network</button>
                    <button class="menubar-item">Delete</button>
                    <button class="menubar-item">Backup/Restore</button>
                    <button class="menubar-item">Language</button>
                    <button class="menubar-item">About</button>
                </div>
                
                <!-- Title Bar -->
                <div class="titlebar">
                    TIS Configuration Software / HomeAssistant Integration / Devices
                </div>
                
                <!-- Toolbar -->
                <div class="toolbar">
                    <button id="scanBtn" class="primary" onclick="try { scanDevices(); } catch(e) { alert('JavaScript Error: ' + e.message); console.error('Button click error:', e); }">🔍 Scan Network</button>
                    <button onclick="refreshTable()">🔄 Refresh</button>
                    <button onclick="fixEntityTypes()">🔧 Fix Entity Types</button>
                    <button onclick="toggleDebug()">🐛 Debug Tool</button>
                </div>
                
                <!-- Gateway Warning -->
                <div id="gatewayWarning" style="display: none; background: #fff3cd; border-bottom: 2px solid #ffc107; padding: 12px 15px;">
                    <strong>⚠️ Configuration Missing:</strong> Gateway IP not configured.
                </div>
                
                <!-- Table Container -->
                <div class="table-container">
                    <table class="devices-table">
                        <thead>
                            <tr>
                                <th style="width: 50px;">Status</th>
                                <th style="width: 80px;">Subnet</th>
                                <th style="width: 80px;">Device</th>
                                <th style="width: 200px;">Model</th>
                                <th style="width: 150px;">IP Address</th>
                                <th style="width: 80px;">Channels</th>
                                <th style="width: 300px;">Description</th>
                                <th style="width: 280px;">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="devicesTableBody">
                            <tr>
                                <td colspan="8" style="text-align: center; padding: 60px; color: #999;">
                                    <div style="font-size: 48px; margin-bottom: 15px;">📱</div>
                                    <div style="font-size: 14px;">No devices found. Click "Scan Network" to discover devices.</div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <!-- Status Bar -->
                <div class="statusbar">
                    <div id="statusText">Ready - Click "Scan Network" to discover devices</div>
                    <div class="progress-container" id="progressContainer">
                        <div class="progress-bar" id="progressBar" style="width: 0%"></div>
                    </div>
                    <div id="deviceCount">Total Devices: 0</div>
                </div>
            </div>

            <script>
                let debugMode = false;
                let debugSocket = null;
                let currentGatewayIP = '';
                
                // Sayfa yüklendiğinde gateway IP kontrolü
                window.addEventListener('DOMContentLoaded', async function() {
                    console.log('Page loaded, fetching gateway info...');
                    try {
                        const response = await fetch('/api/info');
                        const data = await response.json();
                        currentGatewayIP = data.gateway_ip || '';
                        console.log('Gateway IP:', currentGatewayIP);
                        
                        // Gateway IP yoksa veya 0.0.0.0 ise uyarı göster
                        if (!currentGatewayIP || currentGatewayIP === '0.0.0.0') {
                            document.getElementById('gatewayWarning').style.display = 'block';
                        }
                    } catch (e) {
                        console.error('Gateway IP alınamadı:', e);
                    }
                });
                
                function toggleDebug() {
                    alert('Debug tool coming soon!');
                }
                
                function refreshTable() {
                    console.log('Refresh clicked');
                    scanDevices();
                }
                
                async function scanDevices() {
                    console.log('scanDevices() called');
                    const btn = document.getElementById('scanBtn');
                    const statusText = document.getElementById('statusText');
                    const tableBody = document.getElementById('devicesTableBody');
                    const gatewayWarning = document.getElementById('gatewayWarning');
                    const progressContainer = document.getElementById('progressContainer');
                    const progressBar = document.getElementById('progressBar');
                    
                    console.log('Current Gateway IP:', currentGatewayIP);
                    
                    // Gateway IP kontrolü
                    if (!currentGatewayIP || currentGatewayIP === '0.0.0.0') {
                        console.warn('Gateway IP not configured');
                        statusText.innerText = '⚠️ Gateway IP not configured!';
                        gatewayWarning.style.display = 'block';
                        return;
                    }
                    
                    gatewayWarning.style.display = 'none';
                    
                    // Butonları devre dışı bırak
                    btn.disabled = true;
                    document.querySelectorAll('.toolbar button').forEach(b => b.disabled = true);
                    
                    btn.innerText = "⏳ Scanning...";
                    statusText.innerText = "Scanning network, please wait...";
                    tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 40px;"><div style="font-size: 32px;">⏳</div><div>Scanning network...</div></td></tr>';
                    
                    // Progress bar başlat
                    progressContainer.classList.add('active');
                    progressBar.style.width = '0%';
                    
                    // Progress animasyonu (30 saniye boyunca dolacak)
                    const scanDuration = 30000; // 30 saniye
                    const progressInterval = 100; // Her 100ms'de güncelle
                    const progressStep = (progressInterval / scanDuration) * 100;
                    let currentProgress = 0;
                    
                    const progressTimer = setInterval(() => {
                        currentProgress += progressStep;
                        if (currentProgress >= 100) {
                            currentProgress = 100;
                            clearInterval(progressTimer);
                        }
                        progressBar.style.width = currentProgress + '%';
                    }, progressInterval);
                    
                    console.log('Starting SSE stream...');
                    
                    let deviceCount = 0;
                    
                    try {
                        const eventSource = new EventSource('/api/devices/stream?gateway=' + encodeURIComponent(currentGatewayIP));
                        
                        eventSource.addEventListener('start', (e) => {
                            console.log('Stream started');
                            tableBody.innerHTML = '';
                        });
                        
                        eventSource.addEventListener('device', (e) => {
                            const device = JSON.parse(e.data);
                            console.log('Device found:', device);
                            deviceCount++;
                            
                            // Tabloya hemen ekle
                            const row = createDeviceRow(device);
                            tableBody.innerHTML += row;
                            
                            statusText.innerText = `🔍 Scanning... (${deviceCount} device(s) found)`;
                            document.getElementById('deviceCount').innerText = `Total Devices: ${deviceCount}`;
                        });
                        
                        eventSource.addEventListener('complete', (e) => {
                            console.log('Scan completed');
                            clearInterval(progressTimer);
                            progressBar.style.width = '100%';
                            
                            setTimeout(() => {
                                progressContainer.classList.remove('active');
                                progressBar.style.width = '0%';
                            }, 500);
                            
                            statusText.innerText = `✅ Scan completed: ${deviceCount} device(s) found`;
                            
                            if (deviceCount === 0) {
                                tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 60px; color: #999;"><div style="font-size: 48px; margin-bottom: 15px;">❌</div><div>No devices found</div></td></tr>';
                            }
                            
                            eventSource.close();
                            
                            // Butonları tekrar aktif et
                            btn.disabled = false;
                            document.querySelectorAll('.toolbar button').forEach(b => b.disabled = false);
                            btn.innerText = "🔍 Scan Network";
                        });
                        
                        eventSource.onerror = (e) => {
                            console.error('SSE error:', e);
                            clearInterval(progressTimer);
                            progressContainer.classList.remove('active');
                            progressBar.style.width = '0%';
                            
                            statusText.innerText = "❌ Error during scan";
                            eventSource.close();
                            
                            // Butonları tekrar aktif et
                            btn.disabled = false;
                            document.querySelectorAll('.toolbar button').forEach(b => b.disabled = false);
                            btn.innerText = "🔍 Scan Network";
                        };
                        
                    } catch (e) {
                        console.error('Scan error:', e);
                        clearInterval(progressTimer);
                        progressContainer.classList.remove('active');
                        progressBar.style.width = '0%';
                        
                        statusText.innerText = "❌ Error: " + e.message;
                        tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 60px; color: #f44336;"><div style="font-size: 48px; margin-bottom: 15px;">⚠️</div><div>Error: ${e.message}</div></td></tr>`;
                        
                        // Butonları tekrar aktif et
                        btn.disabled = false;
                        document.querySelectorAll('.toolbar button').forEach(b => b.disabled = false);
                        btn.innerText = "🔍 Scan Network";
                    }
                }

                function createDeviceRow(dev) {
                    const addedClass = dev.is_added ? 'added' : '';
                    const statusIcon = dev.is_added ? '<span class="status-icon added">✓</span>' : '';
                    
                    // Eklenmiş cihazlar için Edit+Remove butonları, eklenmemişler için Preview+Add butonları
                    // Laravel Backpack button stilini kullan
                    let actionButtons = '';
                    if (dev.is_added) {
                        actionButtons = `
                            <div class="table-actions">
                                <button class="btn btn-primary" onclick="previewDevice(${dev.subnet}, ${dev.device}, '${dev.name}')" title="Preview device details">
                                    <span>👁️</span> Preview
                                </button>
                                <button class="btn btn-warning" onclick="editDevice(${dev.subnet}, ${dev.device}, '${dev.name}')" title="Edit device settings">
                                    <span>✏️</span> Edit
                                </button>
                                <button class="btn btn-danger" onclick="removeDevice(${dev.subnet}, ${dev.device}, '${dev.name}')" title="Remove from Home Assistant">
                                    <span>🗑️</span> Remove
                                </button>
                            </div>
                        `;
                    } else {
                        actionButtons = `
                            <div class="table-actions">
                                <button class="btn btn-primary" onclick="previewDevice(${dev.subnet}, ${dev.device}, '${dev.name}')" title="Preview device details">
                                    <span>👁️</span> Preview
                                </button>
                                <button class="btn btn-success" onclick="addDevice(${dev.subnet}, ${dev.device}, '${dev.model_name}', ${dev.channels}, '${dev.name}')" title="Add to Home Assistant">
                                    <span>➕</span> Add
                                </button>
                            </div>
                        `;
                    }
                    
                    return `
                        <tr class="${addedClass}" data-subnet="${dev.subnet}" data-device="${dev.device}">
                            <td class="center">${statusIcon}</td>
                            <td>${dev.subnet}</td>
                            <td>${dev.device}</td>
                            <td>${dev.model_name}</td>
                            <td>${dev.host}</td>
                            <td class="center">${dev.channels}</td>
                            <td>${dev.description || dev.model_name}</td>
                            <td>${actionButtons}</td>
                        </tr>
                    `;
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
                            document.getElementById('statusText').innerText = `✅ Command sent to ${subnet}.${deviceId}`;
                        } else {
                            alert('Error: ' + result.message);
                        }
                    } catch (err) {
                        alert('Error: ' + err.message);
                    }
                }

                async function addDevice(subnet, deviceId, modelName, channels, deviceName) {
                    if (!confirm(`Add device to Home Assistant?\\n\\n${deviceName}\\n\\nNote: This may take 20-30 seconds to query all channel names.`)) {
                        return;
                    }

                    try {
                        console.log(`🚀 Starting device add: ${deviceName} (${subnet}.${deviceId})`);
                        console.log(`📊 Model: ${modelName}, Channels: ${channels}`);
                        
                        // Show progress message immediately
                        document.getElementById('statusText').innerText = `⏳ Adding ${deviceName}... (querying ${channels} channel names, please wait 20-30s)`;
                        console.log('⏳ Status: Sending add_device request...');
                        
                        // Skip query_device step - it's unnecessary and just sends packets without waiting for response
                        // Go directly to add_device which does all the real work
                        
                        const startTime = Date.now();
                        
                        // Add device (LONG operation - 15-20 seconds)
                        // No timeout on fetch - let it complete naturally
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
                        
                        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                        console.log(`⏱️ Request completed in ${elapsed}s`);
                        
                        const result = await response.json();
                        console.log('📥 Server response:', result);
                        
                        if (result.success) {
                            console.log('✅ Device added successfully!');
                            alert('✅ Device added successfully!\\n\\n' + result.message);
                            document.getElementById('statusText').innerText = '✅ ' + result.message;
                            // Update table row
                            const row = document.querySelector(`tr[data-subnet="${subnet}"][data-device="${deviceId}"]`);
                            if (row) {
                                row.classList.add('added');
                                const statusCell = row.querySelector('td:first-child');
                                statusCell.innerHTML = '<span class="status-icon added">✓</span>';
                                const actionsCell = row.querySelector('td:last-child');
                                const safeName = deviceName.replace(/'/g, "\\\\'");
                                actionsCell.innerHTML = `
                                    <div class="table-actions">
                                        <button class="btn btn-primary" onclick="previewDevice(${subnet}, ${deviceId}, '${safeName}')" title="Preview device details">
                                            <span>👁️</span> Preview
                                        </button>
                                        <button class="btn btn-warning" onclick="editDevice(${subnet}, ${deviceId}, '${safeName}')" title="Edit device settings">
                                            <span>✏️</span> Edit
                                        </button>
                                        <button class="btn btn-danger" onclick="removeDevice(${subnet}, ${deviceId}, '${safeName}')" title="Remove from Home Assistant">
                                            <span>🗑️</span> Remove
                                        </button>
                                    </div>
                                `;
                            }
                        } else {
                            console.error('❌ Device add failed:', result.message);
                            alert('❌ Error: ' + result.message);
                        }
                    } catch (err) {
                        console.error('❌ Exception during device add:', err);
                        alert('❌ Error: ' + err.message);
                    }
                }

                async function removeDevice(subnet, deviceId, deviceName) {
                    if (!confirm(`Remove device "${deviceName}"?\\n\\nThis will remove the device from Home Assistant.`)) {
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
                            alert('✅ Device removed successfully!\\n\\n' + result.message);
                            document.getElementById('statusText').innerText = '✅ ' + result.message;
                            // Update table row
                            const row = document.querySelector(`tr[data-subnet="${subnet}"][data-device="${deviceId}"]`);
                            if (row) {
                                row.classList.remove('added');
                                const statusCell = row.querySelector('td:first-child');
                                statusCell.innerHTML = '';
                                const actionsCell = row.querySelector('td:last-child');
                                const safeName = deviceName.replace(/'/g, "\\\\'");
                                // Get model and channels from row
                                const modelName = row.cells[3].textContent;
                                const channels = row.cells[5].textContent;
                                actionsCell.innerHTML = `
                                    <div class="table-actions">
                                        <button class="btn btn-primary" onclick="previewDevice(${subnet}, ${deviceId}, '${safeName}')" title="Preview device details">
                                            <span>👁️</span> Preview
                                        </button>
                                        <button class="btn btn-success" onclick="addDevice(${subnet}, ${deviceId}, '${modelName}', ${channels}, '${safeName}')" title="Add to Home Assistant">
                                            <span>➕</span> Add
                                        </button>
                                    </div>
                                `;
                            }
                        } else {
                            alert('❌ Error: ' + result.message);
                        }
                    } catch (err) {
                        alert('❌ Error: ' + err.message);
                    }
                }
                
                function previewDevice(subnet, deviceId, deviceName) {
                    // Preview: Cihaz bilgilerini göster ve test komutları gönder
                    const row = document.querySelector(`tr[data-subnet="${subnet}"][data-device="${deviceId}"]`);
                    if (!row) {
                        alert('Device not found in table');
                        return;
                    }
                    
                    const modelName = row.cells[3].textContent;
                    const ipAddress = row.cells[4].textContent;
                    const channels = row.cells[5].textContent;
                    const description = row.cells[6].textContent;
                    
                    const message = `📱 Device Preview\\n\\n` +
                        `Name: ${deviceName}\\n` +
                        `Address: ${subnet}.${deviceId}\\n` +
                        `Model: ${modelName}\\n` +
                        `IP: ${ipAddress}\\n` +
                        `Channels: ${channels}\\n` +
                        `Description: ${description}\\n\\n` +
                        `Use Edit button to modify settings.`;
                    
                    alert(message);
                    document.getElementById('statusText').innerText = `👁️ Previewing: ${deviceName}`;
                }
                
                function editDevice(subnet, deviceId, deviceName) {
                    // Edit: Cihaz ayarlarını düzenleme popup'ı
                    const newName = prompt(
                        `Edit Device Settings\\n\\n` +
                        `Current Name: ${deviceName}\\n\\n` +
                        `Enter new name (or leave empty to keep current):`,
                        deviceName
                    );
                    
                    if (newName === null) {
                        // User clicked cancel
                        return;
                    }
                    
                    if (newName && newName !== deviceName) {
                        // TODO: Backend'de device name güncelleme API'si eklenebilir
                        alert(`✏️ Edit functionality\\n\\nDevice name would be changed to: ${newName}\\n\\nThis feature requires backend API implementation.`);
                        document.getElementById('statusText').innerText = `✏️ Edit requested for: ${deviceName}`;
                    } else {
                        alert('No changes made.');
                    }
                }
                
                async function fixEntityTypes() {
                    if (!confirm('Fix entity types for all devices?\\n\\nThis will re-detect the correct entity type (switch/light/sensor/etc.) for each device based on its model name.\\n\\nHealthy sensors (TIS-HEALTH-*) will be changed from binary_sensor to sensor.')) {
                        return;
                    }
                    
                    try {
                        document.getElementById('statusText').innerText = '🔄 Fixing entity types...';
                        
                        const response = await fetch('/api/fix_entity_types', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        });
                        
                        const result = await response.json();
                        if (result.success) {
                            alert('✅ Entity types fixed!\\n\\n' + result.message);
                            document.getElementById('statusText').innerText = '✅ Fixed ' + result.fixed_count + ' devices';
                            await refreshTable();  // Refresh to show changes
                        } else {
                            alert('❌ Error: ' + result.message);
                            document.getElementById('statusText').innerText = '❌ Error';
                        }
                    } catch (err) {
                        alert('❌ Error: ' + err.message);
                        document.getElementById('statusText').innerText = '❌ Error';
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

    async def handle_devices_stream(self, request):
        """Handle device discovery with real-time streaming."""
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        )
        await response.prepare(request)
        
        gateway_ip = request.query.get('gateway', self.gateway_ip)
        
        # Load already added devices
        added_devices = set()
        try:
            with open('/config/tis_devices.json', 'r') as f:
                existing_devices = json.load(f)
                added_devices = set(existing_devices.keys())
        except:
            pass
        
        # Send start event
        await response.write(b'event: start\n')
        await response.write(b'data: {"message": "Scanning network..."}\n\n')
        
        # Discover devices with callback for each device found
        from discovery import TISDiscovery
        discovery = TISDiscovery(gateway_ip, self.udp_port)
        
        async def on_device_found(device):
            # Mark if already added
            subnet = device.get('subnet')
            device_id = device.get('device')
            unique_id = f"tis_{subnet}_{device_id}"
            device['is_added'] = unique_id in added_devices
            
            # Send device event immediately
            device_json = json.dumps(device)
            await response.write(b'event: device\n')
            data_line = f'data: {device_json}\n\n'
            await response.write(data_line.encode())
        
        # Run discovery with callback
        try:
            devices = await discovery.discover_with_callback(on_device_found)
        except Exception as e:
            _LOGGER.error(f"Discovery failed: {e}", exc_info=True)
            devices = {}
        
        # Send completion event
        await response.write(b'event: complete\n')
        complete_data = f'data: {{"count": {len(devices)}}}\n\n'
        await response.write(complete_data.encode())
        
        return response

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

    async def handle_query_device(self, request):
        """Query device information (model, channels) by sending discovery messages."""
        try:
            data = await request.json()
            subnet = data.get('subnet')
            device_id = data.get('device_id')

            if subnet is None or device_id is None:
                return web.json_response({'success': False, 'message': 'Eksik parametreler'}, status=400)

            _LOGGER.info(f"🔍 Querying device info: {subnet}.{device_id}")

            # Send OpCode 0xEFFD (Model query) and 0x0003 (Device type query)
            client = TISUDPClient(self.gateway_ip, self.udp_port)
            await client.async_connect(bind=False)  # Send only, no need to bind
            
            # Get local IP for SMARTCLOUD header
            from discovery import get_local_ip
            local_ip = get_local_ip()
            ip_bytes = bytes([int(x) for x in local_ip.split('.')])
            
            # Determine target: Use gateway IP from query parameter if available, otherwise use self.gateway_ip
            # If gateway is 0.0.0.0, use broadcast
            target_ip = self.gateway_ip
            if target_ip == '0.0.0.0' or not target_ip:
                target_ip = '<broadcast>'
            
            # OpCode 0xEFFD: Model query
            packet_effd = TISPacket()
            packet_effd.src_subnet = 1
            packet_effd.src_device = 254
            packet_effd.src_type = 0xFFFE
            packet_effd.tgt_subnet = subnet
            packet_effd.tgt_device = device_id
            packet_effd.op_code = 0xEFFD
            packet_effd.additional_data = b''
            
            tis_data_effd = packet_effd.build()
            full_packet_effd = ip_bytes + b'SMARTCLOUD' + tis_data_effd
            
            if target_ip == '<broadcast>':
                client.send_broadcast(full_packet_effd)
            else:
                client.send_to(full_packet_effd, target_ip)
            _LOGGER.debug(f"Sent OpCode 0xEFFD (Model query) to {subnet}.{device_id} via {target_ip}")
            
            # OpCode 0x0003: Device type query
            packet_0003 = TISPacket()
            packet_0003.src_subnet = 1
            packet_0003.src_device = 254
            packet_0003.src_type = 0xFFFE
            packet_0003.tgt_subnet = subnet
            packet_0003.tgt_device = device_id
            packet_0003.op_code = 0x0003
            packet_0003.additional_data = b''
            
            tis_data_0003 = packet_0003.build()
            full_packet_0003 = ip_bytes + b'SMARTCLOUD' + tis_data_0003
            
            if target_ip == '<broadcast>':
                client.send_broadcast(full_packet_0003)
            else:
                client.send_to(full_packet_0003, target_ip)
            _LOGGER.debug(f"Sent OpCode 0x0003 (Device type query) to {subnet}.{device_id} via {target_ip}")
            
            client.close()
            
            return web.json_response({
                'success': True,
                'message': f'Discovery messages sent to {subnet}.{device_id}'
            })
        except Exception as e:
            _LOGGER.error(f"Query device error: {e}")
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
    
    def _detect_entity_type(self, model_name: str) -> str:
        """Detect Home Assistant entity type from device model name."""
        model = model_name.upper()
        
        # LIGHT - Dimmer devices
        if any(x in model for x in ['DIM-', 'VLC-', 'DALI-']):
            return 'light'
        
        # CLIMATE - HVAC/Thermostat
        if any(x in model for x in ['-AC', 'HVAC', 'VAV']):
            # But not for AC panel switches
            if 'AC-4G' in model or 'AC4G' in model:
                return 'switch'
            return 'climate'
        
        # COVER - Curtain/Motor
        if any(x in model for x in ['TIS-M', 'TIS-TM', 'CURTAIN', 'MOTOR', 'LFT-']):
            return 'cover'
        
        # BINARY SENSOR - Motion/Occupancy sensors (digital state only)
        if any(x in model for x in ['PIR', 'OS-MMV2']):
            return 'binary_sensor'
        
        # SENSOR - Health, Temperature, Humidity, Energy sensors
        if any(x in model for x in ['HEALTH-CM', 'HEALTH-SENSOR', '4T-IN', 'ES-10F-CM', '4AI-', '4CH-AIN', 'WS-71']):
            return 'sensor'
        
        # Default: Switch (relay)
        return 'switch'

    async def handle_add_device(self, request):
        """Handle add device to Home Assistant request."""
        try:
            data = await request.json()
            subnet = data.get('subnet')
            device_id = data.get('device_id')
            model_name = data.get('model_name')
            channels = data.get('channels', 1)
            device_name = data.get('device_name')

            _LOGGER.info(f"📥 Add device request: subnet={subnet}, device_id={device_id}, model={model_name}, channels={channels}, name={device_name}")

            if not all([subnet, device_id, model_name]):
                return web.json_response({'success': False, 'message': 'Eksik parametreler'}, status=400)

            _LOGGER.info(f"Adding device: {subnet}.{device_id} - {device_name} ({channels} channels)")
            
            # Query channel names from device BEFORE saving
            channel_names = {}
            initial_states = {}
            
            if channels > 1:  # Only for multi-channel devices
                try:
                    _LOGGER.info(f"Querying channel names for {subnet}.{device_id}...")
                    channel_names = await self._query_channel_names(subnet, device_id, channels)
                    _LOGGER.info(f"Received {len(channel_names)} channel names: {list(channel_names.keys())}")
                except Exception as e:
                    _LOGGER.error(f"Failed to query channel names: {e}", exc_info=True)
                    # Continue without channel names
                
                # Query initial states for all channels
                try:
                    _LOGGER.info(f"Querying initial states for {subnet}.{device_id}...")
                    initial_states = await self._query_initial_states(subnet, device_id, channels)
                    _LOGGER.info(f"Received states for {len(initial_states)} channels")
                except Exception as e:
                    _LOGGER.error(f"Failed to query initial states: {e}", exc_info=True)
                    # Continue without initial states
            else:
                _LOGGER.warning(f"⚠️ Channels = {channels}, skipping queries (expected > 1)")
                _LOGGER.debug(f"Single channel device, skipping queries")
            
            unique_id = f"tis_{subnet}_{device_id}"
            
            # Detect entity type from model name
            entity_type = self._detect_entity_type(model_name)
            _LOGGER.info(f"Detected entity type: {entity_type} for model {model_name}")
            
            device_info = {
                'subnet': subnet,
                'device_id': device_id,
                'model_name': model_name,
                'channels': channels,
                'name': device_name or f"{model_name} ({subnet}.{device_id})",
                'channel_names': channel_names,  # Add channel names to JSON
                'initial_states': initial_states,  # Add initial states
                'entity_type': entity_type  # NEW: Entity type for HA
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
            _LOGGER.error(f"Add device error: {e}", exc_info=True)
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
            _LOGGER.error(f"Remove device error: {e}", exc_info=True)
            return web.json_response({'success': False, 'message': f'❌ Hata: {str(e)}'}, status=500)

    async def handle_fix_entity_types(self, request):
        """Fix entity_type for all devices by re-detecting from model names."""
        try:
            devices_file = '/config/tis_devices.json'
            
            # Load devices
            try:
                with open(devices_file, 'r') as f:
                    devices = json.load(f)
            except FileNotFoundError:
                return web.json_response({'success': False, 'message': 'Cihaz dosyası bulunamadı'}, status=404)
            
            if not devices:
                return web.json_response({'success': False, 'message': 'Kayıtlı cihaz yok'}, status=404)
            
            # Re-detect entity types
            fixed_devices = []
            unchanged_devices = []
            
            for device_id, device_data in devices.items():
                model_name = device_data.get('model_name', '')
                old_entity_type = device_data.get('entity_type', 'unknown')
                
                # Re-detect using current logic
                new_entity_type = self._detect_entity_type(model_name)
                
                if old_entity_type != new_entity_type:
                    device_data['entity_type'] = new_entity_type
                    device_name = device_data.get('name', device_id)
                    fixed_devices.append(f"{device_name}: {old_entity_type} → {new_entity_type}")
                    _LOGGER.info(f"Fixed {device_id} ({model_name}): {old_entity_type} → {new_entity_type}")
                else:
                    unchanged_devices.append(device_data.get('name', device_id))
            
            # Save updated devices
            with open(devices_file, 'w') as f:
                json.dump(devices, f, indent=2, ensure_ascii=False)
            
            # Build response message
            if fixed_devices:
                message = f"✅ {len(fixed_devices)} cihaz düzeltildi:\n\n"
                message += "\n".join(f"  • {d}" for d in fixed_devices[:10])  # Show max 10
                if len(fixed_devices) > 10:
                    message += f"\n  ... ve {len(fixed_devices) - 10} cihaz daha"
                
                if unchanged_devices:
                    message += f"\n\n✓ {len(unchanged_devices)} cihaz zaten doğru"
                
                message += "\n\n🔄 TIS entegrasyonunu yenileyin:\nSettings → Integrations → TIS → ⋮ → Reload"
                
                # Try to reload automatically
                reload_success = await self._reload_tis_integration()
                if reload_success:
                    message += "\n\n✅ Entegrasyon otomatik olarak yenilendi!"
            else:
                message = f"✓ Tüm {len(unchanged_devices)} cihaz zaten doğru entity_type'a sahip"
            
            return web.json_response({
                'success': True,
                'message': message,
                'fixed_count': len(fixed_devices),
                'unchanged_count': len(unchanged_devices)
            })
            
        except Exception as e:
            _LOGGER.error(f"Fix entity types error: {e}", exc_info=True)
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
    
    async def _query_channel_names(self, subnet: int, device_id: int, channels: int) -> dict:
        """Query channel names from device via UDP with retry logic."""
        try:
            from discovery import query_all_channel_names
            
            _LOGGER.info(f"🔍 Querying channel names for {subnet}.{device_id} ({channels} channels)")
            
            # Use the reliable discovery function with retries and delays
            channel_names = await query_all_channel_names(
                self.gateway_ip, 
                subnet, 
                device_id, 
                channels, 
                self.udp_port
            )
            
            _LOGGER.info(f"✅ Query complete: {len(channel_names)}/{channels} names retrieved")
            
            # Convert integer keys to strings for JSON compatibility
            result = {str(k): v for k, v in channel_names.items()}
            
            return result
            
        except Exception as e:
            _LOGGER.error(f"❌ Failed to query channel names: {e}", exc_info=True)
            return {}
    
    async def _query_initial_states(self, subnet: int, device_id: int, channels: int) -> dict:
        """Query initial channel states from device."""
        try:
            from discovery import query_device_initial_states
            
            _LOGGER.info(f"🔍 Querying initial states for {subnet}.{device_id}")
            
            # Query all channel states
            states = await query_device_initial_states(
                self.gateway_ip,
                subnet,
                device_id,
                channels,
                self.udp_port
            )
            
            _LOGGER.info(f"✅ States query complete: {len(states)}/{channels} channels")
            
            # Convert to JSON-serializable format
            result = {}
            for ch, state in states.items():
                result[str(ch)] = {
                    'is_on': state['is_on'],
                    'brightness': state['brightness'],
                    'raw_value': state['raw_value']
                }
            
            return result
            
        except Exception as e:
            _LOGGER.error(f"❌ Failed to query initial states: {e}", exc_info=True)
            return {}


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='TIS Web UI Server')
    parser.add_argument('--gateway', default='192.168.1.200', help='TIS Gateway IP')
    parser.add_argument('--port', type=int, default=6000, help='UDP Port')
    parser.add_argument('--log-level', default='info', choices=['debug', 'info', 'warning', 'error'], help='Log level')
    args = parser.parse_args()
    
    # Set log level from argument
    log_level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR
    }
    logging.getLogger().setLevel(log_level_map[args.log_level])
    _LOGGER.setLevel(log_level_map[args.log_level])
    _LOGGER.info(f"Log level set to: {args.log_level.upper()}")

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
