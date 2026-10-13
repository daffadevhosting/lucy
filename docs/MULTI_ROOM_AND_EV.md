# Multi-room / Multi-ESP32 Discovery + Mode Mobil EV

Lucy v1.1 mendukung:

1. **Multi-room home** — banyak ESP32 di ruangan berbeda, auto-discovery
2. **Vehicle (EV) mode** — arsitektur yang sama untuk mobil listrik

---

## Arsitektur Discovery

```text
ESP32 Node (boot)
      │
      ▼
 lucy/discovery/announce
      │  { node_id, profile, devices[], fw, ip }
      ▼
 Lucy DeviceManager  ←── update live registry (online/offline)
      │
      ▼
 LLM prompt otomatis berisi daftar device + status
```

### Topic Convention

| Arah | Topic | Keterangan |
|------|-------|------------|
| ESP32 → Lucy | `lucy/discovery/announce` | Node announce saat boot / request |
| Lucy → ESP32 | `lucy/discovery/request` | Minta semua node announce ulang |
| Lucy → ESP32 | `lucy/{profile}/devices/{id}/set` | Perintah |
| ESP32 → Lucy | `lucy/{profile}/devices/{id}/status` | Status + heartbeat |

`profile` = `home` atau `vehicle`

---

## Mode HOME (Multi-room)

1. Edit `config/devices.yaml` — isi `room` + `node_id`
2. Flash tiap ESP32 (`lucy_node.ino`) — bedakan `NODE_ID` & `MY_DEVICES[]`
3. Lucy auto-discover saat start

Contoh perintah:
- "Nyalakan lampu teras"
- "Matikan kipas ruang tamu"
- "Set AC kamar ke 24"

---

## Mode VEHICLE (Mobil EV)

Di `config/devices.yaml`:

```yaml
profile: vehicle
```

Zona: cabin | exterior | climate | doors | power

**Peringatan:** jangan hubungkan ke sistem safety-critical (rem, steering, HV battery).

Firmware: `lucy_vehicle_node.ino`

---

## Menambah Node Baru

1. Tambah entry di `devices.yaml`
2. Flash ESP32 dengan `NODE_ID` dan `MY_DEVICES` yang sesuai
3. Restart Lucy → node announce → online
