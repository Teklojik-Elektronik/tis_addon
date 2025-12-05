# Changelog

## [1.0.2] - 2025-12-05

### ⚠️ ÖNEMLI: Addon'u Yeniden Başlatın!
Bu sürüme güncelledikten sonra **mutlaka addon'u yeniden başlatın**:
1. Settings → Add-ons → TIS Akıllı Ev Sistemi
2. ⋮ → Restart

### Eklenenler
- **Kanal İsimleri Otomatik Sorgulanıyor**: Web UI'dan cihaz eklenirken tüm kanal isimleri cihazdan okunuyor
- **Otomatik Entegrasyon Reload**: `hassio_role: manager` ile entegrasyon otomatik yenileniyor
- **Entegrasyon Silme Temizliği**: Entegrasyon silindiğinde tüm cihazlar ve JSON dosyası temizleniyor
- **Web UI Cihaz Senkronizasyonu**: Ekleme/silme işlemleri tarama yapmadan UI'da güncelleniyor

### Düzeltilenler
- Web UI cihaz kartı silme sorunu (data-attribute ile kesin bulma)
- Kanal isim decode işleminde 0xFF değerleri filtreleniyor
- Import JSON gereksiz tekrarları kaldırıldı
- Detaylı hata logları (exc_info=True)

### Değişenler
- `config.yaml`: `hassio_role: default` → `hassio_role: manager`
- `manifest.json`: version 1.1.0
- Kanal isimleri JSON'a `channel_names` field'ı ile kaydediliyor

### Teknik Detaylar
- `_query_channel_names()`: OpCode 0xF00E ile kanal isimleri sorgulanıyor
- `async_remove_entry()`: Entegrasyon silindiğinde tam temizlik
- `channel_names` dict: {1: "KORİDOR TEKLİ", 2: "KORİDOR ÇİFT", ...}

---

## [1.0.1] - 2025-12-04

### İlk Sürüm
- UDP Discovery
- Web UI cihaz yönetimi
- Debug tool
- 191 cihaz tipi desteği
