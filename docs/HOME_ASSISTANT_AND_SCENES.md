# Home Assistant Integration + Scenes / Group Commands

## 1. Home Assistant MQTT Discovery

Lucy mem-publish entity ke Home Assistant lewat **MQTT Discovery**.

### Setup di Home Assistant

1. Pastikan **MQTT integration** aktif dan terhubung ke broker yang sama (Mosquitto di Pi).
2. Di HA → Settings → Devices & Services → MQTT → pastikan "Enable discovery" ON.
3. Jalankan Lucy dengan:

```env
HA_DISCOVERY=true
```

4. Saat start, Lucy publish config ke:
   ```
   homeassistant/switch/lucy_lampu_teras/config
   homeassistant/light/...
   homeassistant/climate/...
   homeassistant/lock/...
   ```

5. Entity muncul otomatis di HA (switch, light, climate, lock, cover, fan).

### Mapping tipe

| Lucy type | HA component |
|-----------|--------------|
| relay / power | switch |
| light / headlight | light |
| fan | fan |
| ac / climate | climate |
| lock | lock |
| window | cover |

### Kontrol dua arah

- Suara Lucy → MQTT → ESP32 (dan state ke HA)
- HA UI / automation → MQTT command topic → ESP32
- Status ESP32 → `.../status` → HA state

---

## 2. Scenes

File: `config/scenes.yaml`

### Scene bawaan (home)

| scene_id | Efek |
|----------|------|
| `mode_malam` | Lampu utama OFF, lampu kamar ON, AC 25° |
| `mode_pagi` | Lampu ruang tamu & dapur ON, kamar OFF |
| `semua_mati` | Semua perangkat OFF |
| `mode_tamu` | Lampu ruang tamu + teras ON |

### Scene vehicle

| scene_id | Efek |
|----------|------|
| `mode_parkir` | Kunci, AC off, lampu off |
| `mode_perjalanan` | AC on, eco off |

### Contoh suara

- "Lucy, aktifkan mode malam"
- "Mode pagi"
- "Matikan semuanya"
- "Mode parkir" (di mobil)

---

## 3. Group Commands

| group_id | Match |
|----------|--------|
| `semua_lampu` | type: relay, light, headlight |
| `lampu_ruang_tamu` | room: ruang_tamu + type relay/light |
| `semua_ac` | type: ac, climate |

### Contoh suara

- "Matikan semua lampu"
- "Nyalakan semua AC"

---

## 4. Menambah Scene Baru

Edit `config/scenes.yaml` — tidak perlu ubah kode Python, cukup restart Lucy.

## 5. Tips

- Pastikan `device_id` di scene cocok dengan `devices.yaml`.
- Satu broker MQTT untuk Lucy + HA + semua ESP32.
- Nonaktifkan discovery: `HA_DISCOVERY=false`
