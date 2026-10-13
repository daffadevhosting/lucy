# Custom Wake Word: "Hey Lucy"

Lucy mendukung custom wake word offline menggunakan **Picovoice Porcupine**.

---

## 1. Buat Model "Hey Lucy" di Picovoice Console

1. Buka → [https://console.picovoice.ai/](https://console.picovoice.ai/)
2. Login / daftar (gratis).
3. Masuk ke menu **Porcupine** → **Custom Keywords**.
4. Klik **Create New Keyword**.
5. Isi:
   - **Phrase**: `Hey Lucy` (atau `Hey Lucy.` — coba beberapa variasi)
   - **Language**: English (Porcupine custom keyword saat ini paling stabil di English)
6. Pilih platform yang kamu pakai:
   - **Raspberry Pi** (armv7 / aarch64) → pilih `Raspberry Pi`
   - Atau `Linux (x86_64)` jika testing di laptop
7. Klik **Train** / **Download**.
8. Kamu akan mendapat file `.ppn`, contoh nama:
   ```
   hey_lucy_raspberry-pi.ppn
   ```

> **Tips akurasi**
> - Rekam dengan aksen yang mirip user utama.
> - Bisa buat beberapa model (laki-laki / perempuan) lalu load dual keyword.
> - Sensitivity 0.55–0.70 biasanya sweet spot.

---

## 2. Letakkan Model di Project

```bash
mkdir -p models/wakewords
# pindahkan file hasil download
mv ~/Downloads/hey_lucy_raspberry-pi.ppn models/wakewords/
```

Struktur yang diharapkan:
```
lucy/
└── models/
    └── wakewords/
        └── hey_lucy_raspberry-pi.ppn
```

---

## 3. Konfigurasi `.env`

```env
PORCUPINE_ACCESS_KEY=your_picovoice_access_key_here
PORCUPINE_KEYWORD_PATH=models/wakewords/hey_lucy_raspberry-pi.ppn
PORCUPINE_SENSITIVITY=0.65
```

Jika `PORCUPINE_KEYWORD_PATH` kosong, Lucy akan fallback ke built-in keyword (`porcupine`).

---

## 4. Jalankan

```bash
python run.py
```

Log yang muncul:
```
WakeWord ready | model=['.../hey_lucy_raspberry-pi.ppn'] | sensitivity=[0.65]
Listening for wake word "Hey Lucy"...
```

Ucapkan **"Hey Lucy"** → Lucy langsung merekam perintahmu.

---

## 5. Multi Keyword (Opsional)

Kamu bisa load beberapa model sekaligus (misalnya "Hey Lucy" + "Computer"):

```python
# di assistant.py atau saat inisialisasi
self.wake = WakeWordDetector(
    keyword_paths=[
        "models/wakewords/hey_lucy_raspberry-pi.ppn",
        "models/wakewords/computer_raspberry-pi.ppn",
    ],
    sensitivities=[0.65, 0.55],
)
```

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `FileNotFoundError` | Cek path di `.env` dan pastikan file `.ppn` ada |
| Sering false positive | Turunkan `PORCUPINE_SENSITIVITY` ke 0.5 |
| Susah terdeteksi | Naikkan sensitivity ke 0.7–0.75 atau retrain model |
| Sample rate mismatch | Porcupine selalu 16 kHz — jangan ubah `SAMPLE_RATE` |
| Platform salah | Download ulang `.ppn` yang sesuai architecture (Pi 4/5 = aarch64) |

---

## Catatan Penting

- Model `.ppn` **platform-specific**. Model untuk Raspberry Pi **tidak** jalan di laptop x86, dan sebaliknya.
- Access Key Picovoice wajib (free tier cukup untuk development).
- Custom keyword English lebih akurat daripada mencoba memaksa frasa Indonesia saat ini.
