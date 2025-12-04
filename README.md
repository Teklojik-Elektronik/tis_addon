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
5. **Configuration** sekmesinden **gateway_ip** değerini girin (TIS gateway IP adresi)
6. **Save** → **Start** butonuna tıklayın
7. **Web kullanıcı arayüzünü aç** butonuna tıklayarak cihazlarınızı yönetin!

### Lokal Test (Geliştirme)

Windows PowerShell'de:

```powershell
cd C:\xampp\htdocs\tis_addon
.\test.ps1
```

Tarayıcınızda açın: `http://localhost:8888`

## ⚙️ Yapılandırma

**Kurulumdan sonra mutlaka yapılandırın:**

1. Addon sayfasında **Configuration** sekmesine gidin
2. **Gateway IP** alanına TIS gateway cihazınızın IP adresini girin
3. **UDP Port** varsayılan olarak 6000'dir (değiştirmenize gerek yok)
4. **Save** tıklayın
5. Addon'u **Start** edin

```yaml
gateway_ip: ""              # TIS gateway IP (ÖRN: 192.168.1.200)
udp_port: 6000               # UDP iletişim portu
log_level: info              # Log seviyesi
```

## 🎯 Kullanım

### Addon Kurulumu (İlk Adım)

1. Addon başlatıldıktan sonra **"Web kullanıcı arayüzünü aç"** butonuna tıklayın
2. **Gateway IP** kutusuna TIS gateway adresinizi girin (veya Configuration'dan ayarlayın)
3. **"Cihazları Tara"** butonuna basarak ağınızdaki TIS cihazlarını keşfedin
4. Her cihazın **"Ekle"** butonuna tıklayarak cihazı sisteme kaydedin

### TIS Entegrasyonu Kurulumu (İkinci Adım)

Addon ile eklediğiniz cihazları Home Assistant'ta görmek için **TIS Entegrasyonunu** kurmalısınız:

1. **Settings → Devices & Services → Add Integration**
2. **"TIS"** arayın ve entegrasyonu ekleyin
3. Gateway IP ve UDP Port bilgilerini girin (addon ile aynı olmalı)
4. Entegrasyon kurulduktan sonra eklediğiniz cihazlar **switch** olarak görünecek

### Yeni Cihaz Ekleme

Addon'dan yeni bir cihaz eklediğinizde:

1. Web UI'dan **"Ekle"** butonuna tıklayın
2. Cihaz `/config/tis_devices.json` dosyasına kaydedilecek
3. **Manuel olarak** Settings → Integrations → **TIS** → **⋮ (üç nokta)** → **Reload** yapın
4. Yeni cihazlar entity listesine eklenecek

> **Not:** Şu anda otomatik reload çalışmıyor, manuel reload yapmanız gerekiyor. Home Assistant restart'a gerek yok!

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
- **Gateway IP** adresini Web UI'deki input kutusundan veya Configuration sekmesinden doğru girin
- Gateway cihazının IP adresini öğrenmek için TIS uygulamasından bakın
- Cihazların açık ve ağa bağlı olduğunu kontrol edin
- Firewall ayarlarını kontrol edin (UDP port 6000)
- Home Assistant ile gateway aynı ağda mı kontrol edin

### Eklediğim cihazlar sensör olarak görünmüyor
- **TIS Entegrasyonunu kurduğunuzdan emin olun** (Settings → Integrations → Add → TIS)
- Yeni cihaz ekledikten sonra **TIS entegrasyonunu reload** edin:
  - Settings → Integrations → TIS → ⋮ → Reload
- Entegrasyon kurulmadan önce addon'dan eklediğiniz cihazlar:
  - Entegrasyonu kurduktan sonra otomatik olarak yüklenecektir

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
