# TIS-HEALTH-CM Sensör Sorunu - Çözüm

## Sorun
TIS-HEALTH-CM cihazı addon tarafından başarıyla eklendi ancak Home Assistant entegrasyonunda görünmüyor.

**Sebep:** Addon, TIS-HEALTH-CM cihazlarını yanlışlıkla `binary_sensor` olarak sınıflandırıyordu. Oysa bu cihazlar `sensor` platformunda olmalı (sıcaklık, nem, CO2, VOC gibi sağlık metrikleri sağlarlar).

## Yapılan Düzeltmeler

### 1. Addon (tis_addon/web_ui.py)
- `_detect_entity_type()` fonksiyonunda TIS-HEALTH-CM ve HEALTH-SENSOR'ü `binary_sensor` yerine `sensor` platformuna taşındı
- Yeni API endpoint eklendi: `/api/fix_entity_types` - Mevcut tüm cihazların entity_type'larını otomatik düzeltir
- Web UI'ye "🔧 Fix Entity Types" butonu eklendi

### 2. Home Assistant Entegrasyonu
Entegrasyon zaten doğru yapılandırılmış durumda:
- ✅ `sensor.py` hazır ve health sensor desteği var
- ✅ `device_appliance_mapping.py`'de TIS-HEALTH-CM için `health_sensor: 1` tanımlı
- ✅ `const.py`'de HEALTH_SENSOR_TYPES tanımlı (temperature, humidity, co2, voc, pm25, luminance, noise)

## Çözüm Adımları

### Adım 1: Addon'u Yeniden Derle
```bash
# Home Assistant'ta:
# 1. Settings → Add-ons → TIS Addon
# 2. "Rebuild" butonuna tıklayın
# 3. Addon yeniden başlatılacak
```

### Adım 2: Mevcut Cihazların Entity Type'ını Düzelt

**Otomatik Yöntem (Önerilen):**
1. TIS Addon Web UI'yi açın: http://homeassistant.local:8888
2. Üst toolbar'da "🔧 Fix Entity Types" butonuna tıklayın
3. Onaylayın - Tüm cihazların entity_type'ları düzeltilecek
4. Entegrasyon otomatik olarak yenilenecek

**Manuel Yöntem:**
Eğer otomatik yöntem çalışmazsa:
1. Home Assistant'ta: Settings → Integrations → TIS
2. ⋮ (üç nokta) → Reload

### Adım 3: Yeni Cihaz Ekle (Tekrar)
Eğer TIS-HEALTH-CM hala görünmüyorsa:
1. TIS Addon Web UI'de cihazı "Remove" edin
2. Sonra tekrar "Add" edin (şimdi doğru entity_type ile eklenecek)
3. Entegrasyonu yenileyin

## Sonuç
TIS-HEALTH-CM artık Home Assistant'ta sensor olarak görünecek ve şu metrikleri sağlayacak:
- 🌡️ Sıcaklık (Temperature)
- 💧 Nem (Humidity)
- 🌫️ CO2 seviyesi
- 🧪 VOC (Uçucu Organik Bileşikler)
- 🌫️ PM2.5 (Partikül Madde)
- ☀️ Işık seviyesi (Luminance)
- 🔊 Gürültü seviyesi (Noise)

## Teknik Detaylar

### Entity Type Eşleştirmeleri
```python
# Eski (YANLIŞ):
'PIR', 'HEALTH-CM', 'HEALTH-SENSOR', 'OS-MMV2' → binary_sensor

# Yeni (DOĞRU):
'PIR', 'OS-MMV2' → binary_sensor  # Motion/occupancy only
'HEALTH-CM', 'HEALTH-SENSOR' → sensor  # Health metrics
```

### Device Mapping
```python
# device_appliance_mapping.py
"TIS-HEALTH-CM": {"health_sensor": 1},
"TIS-HEALTH-CM-RADAR": {"health_sensor": 1},
```

### Sensor Types
```python
# const.py
HEALTH_SENSOR_TYPES = {
    "temperature": "Temperature",
    "humidity": "Humidity", 
    "co2": "CO2",
    "voc": "VOC",
    "pm25": "PM2.5",
    "luminance": "Illuminance",
    "noise": "Noise Level",
}
```

## Commit Bilgileri
- **tis_addon**: Commit 37d4e1b - "fix: Correct entity_type detection for TIS-HEALTH sensors"
- **Tarih**: 8 Aralık 2024

## Test Edilmesi Gerekenler
- [x] Addon rebuild sonrası yeni eklenen TIS-HEALTH-CM doğru entity_type (sensor) ile ekleniyor mu?
- [ ] Fix Entity Types butonu mevcut cihazları düzeltiyor mu?
- [ ] TIS-HEALTH-CM sensörleri Home Assistant'ta görünüyor mu?
- [ ] Sensör değerleri (sıcaklık, nem vb.) doğru okunuyor mu?

## Log Kontrol
Addon loglarında şunu göreceksiniz:
```
INFO:__main__:Detected entity_type: sensor for model TIS-HEALTH-CM
```

Entegrasyon loglarında:
```
INFO:custom_components.tis.sensor:Setting up TIS sensor entities
INFO:custom_components.tis.sensor:Device TIS-HEALTH-CM supports health_sensor
```
