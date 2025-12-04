# TIS Akıllı Ev Sistemi - Dokümantasyon

## Özellikler

- UDP üzerinden TIS cihazlarıyla iletişim
- Otomatik cihaz keşfi
- Web tabanlı kontrol paneli
- Gerçek zamanlı durum güncelleme

## Desteklenen Cihazlar

191 farklı TIS cihaz tipi desteklenmektedir:
- Temel kontrolörler
- Dimmer'lar
- RGB kontrolörler
- Perde motorları
- Termostatlar
- Sensörler

## Teknik Detaylar

- **Protokol**: TIS UDP (Port 6000)
- **Web UI**: Port 8888
- **Discovery**: OpCode 0xF003/0xF004
- **Paket Format**: SMARTCLOUD header + TIS data
