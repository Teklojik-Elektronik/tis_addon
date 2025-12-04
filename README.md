# TIS Akıllı Ev Sistemi Addon

![TIS Logo](https://raw.githubusercontent.com/yourusername/tis-homeassistant-addon/main/icon.png)

TIS cihazlarınızı yönetmek için web tabanlı arayüz. Home Assistant addon olarak kolayca kurabilirsiniz.

## 🚀 Özellikler

- ✅ Otomatik cihaz keşfi (UDP broadcast)
- ✅ 191 farklı TIS cihaz tipi desteği
- ✅ Modern ve kullanıcı dostu web arayüzü
- ✅ Gerçek zamanlı cihaz kontrolü
- ✅ SMARTCLOUD gateway desteği

## 📦 Kurulum

### Home Assistant'a Addon Olarak Kurulum

1. **Supervisor → Add-on Store** menüsüne gidin
2. Sağ üst köşedeki **⋮ (üç nokta)** → **Repositories** tıklayın
3. Şu URL'yi ekleyin:
   ```
   https://github.com/yourusername/tis-homeassistant-addon
   ```
4. **TIS Akıllı Ev Sistemi** addon'unu bulun ve **Install** tıklayın
5. Ayarlardan **gateway_ip** değerini düzenleyin (varsayılan: 192.168.1.200)
6. **Start** butonuna tıklayın
7. **Web kullanıcı arayüzünü aç** butonuna tıklayarak cihazlarınızı yönetin!

### Lokal Test (Geliştirme)

Windows PowerShell'de:

```powershell
cd C:\xampp\htdocs\tis_addon
.\test.ps1
```

Tarayıcınızda açın: `http://localhost:8888`

## ⚙️ Yapılandırma

Addon ayarları:

```yaml
gateway_ip: "192.168.1.200"  # TIS gateway IP adresi
udp_port: 6000               # UDP iletişim portu
```

## 🎯 Kullanım

1. Addon başlatıldıktan sonra **"Web kullanıcı arayüzünü aç"** butonuna tıklayın
2. **"Cihazları Tara"** butonuna basarak ağınızdaki TIS cihazlarını keşfedin
3. Her cihaz için **"Aç"** veya **"Kapat"** butonlarını kullanın
4. Cihazlar 30 saniyede bir otomatik olarak yenilenir

## 📱 Desteklenen Cihazlar

- 💡 Dimmer'lar ve LED kontrolörler
- 🌈 RGB kontrolörler
- 🔌 Röle modülleri
- 🪟 Perde motorları
- 🌡️ Termostatlar
- 📡 Sensörler
- Ve 191+ farklı TIS cihaz modeli!

## 🔧 Teknik Detayler

- **Protokol**: TIS UDP (Port 6000)
- **Web UI Port**: 8888
- **Discovery**: OpCode 0xF003/0xF004
- **Paket Formatı**: SMARTCLOUD header + TIS data (27+ bytes)
- **Network Detection**: Otomatik Ethernet/WiFi interface tespiti

## 🐛 Sorun Giderme

### Cihazlar bulunamıyor
- Gateway IP adresinin doğru olduğundan emin olun
- Cihazların açık ve ağa bağlı olduğunu kontrol edin
- Firewall ayarlarını kontrol edin (UDP port 6000)

### Web arayüzüne ulaşılamıyor
- Addon'un çalıştığından emin olun (Yeşil durum göstergesi)
- Port 8888'in başka bir uygulama tarafından kullanılmadığını kontrol edin

### Log kayıtlarını görüntüleme
- Addon sayfasında **Log** sekmesine tıklayın
- Detaylı hata mesajları için logları inceleyin

## 📄 Lisans

MIT License

## 🤝 Katkıda Bulunma

Pull request'ler ve issue'lar memnuniyetle karşılanır!

## 📞 İletişim

- GitHub: [yourusername/tis-homeassistant-addon](https://github.com/yourusername/tis-homeassistant-addon)
- Issues: [Report a bug](https://github.com/yourusername/tis-homeassistant-addon/issues)
