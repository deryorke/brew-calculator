# Tes otomatis Brew Calculator

Satu perintah menjalankan semua pemeriksaan terhadap folder situs `brew-calculator-pwa`.

## Sekali saja: pasang kebutuhan

```
pip install playwright
playwright install chromium
```

Butuh Python 3.8 atau lebih baru. Tes memakai browser Chromium sendiri dan menyalakan server lokal di komputermu, jadi tidak ada yang dikirim ke internet.

## Menjalankan

Dari folder yang berisi `brew-calculator-pwa` dan `tools`:

```
python3 tools/tests/run-tests.py                    # semua suite
python3 tools/tests/run-tests.py --list             # daftar suite dan isinya
python3 tools/tests/run-tests.py --only logic,ui    # sebagian saja
python3 tools/tests/run-tests.py --fail-fast        # berhenti di kegagalan pertama
python3 tools/tests/run-tests.py --site folder/lain # situs di tempat lain
```

Di Windows ganti `python3` dengan `python` atau `py`. Seluruh rangkaian butuh beberapa menit. Kode keluar 0 berarti semua lolos, 1 berarti ada yang gagal (cocok untuk otomatisasi).

Hasilnya satu baris per suite, misalnya `PASS  logic   119/119   4.2s`. Jika ada yang gagal, nama pemeriksaan dan rincian singkatnya ikut ditampilkan.

## Isi suite

| Suite | Yang diperiksa |
|---|---|
| `logic` | hitungan kalkulator, resep bawaan, mesin timer dengan jam palsu, pembersihan data tersimpan |
| `validation` | aturan input ketat: angka, nama, rasio, suhu, perkiraan waktu |
| `ui` | klik sungguhan: kalkulator, timer, resep, satuan, pengaturan, bahasa |
| `backup` | ekspor dan impor resep, favorit, pengaturan, termasuk berkas berbahaya |
| `datasafety` | permintaan penyimpanan permanen dan pengingat cadangan |
| `alerts` | getaran, notifikasi, dan pekerja timer di latar belakang |
| `ics` | berkas pengingat kalender untuk seduhan panjang |
| `restore` | seduhan yang berjalan bertahan setelah reload; data rusak diabaikan |
| `accessibility` | judul, kontras, ukuran sentuh, fokus, pengumuman, zoom |
| `resilience` | data rusak, penyimpanan diblokir, offline, alur pembaruan |
| `hostcache` | pembaruan tetap sampai walau hosting menyimpan berkas 10 menit |
| `autoversion` | perilaku `stamp-version.py` dan deteksi pembaruan otomatis |

Sebelum suite-suite itu, runner juga memeriksa bahwa versi di `sw.js` sudah diperbarui oleh `stamp-version.py`.

## Batasan

- Semua tes berjalan di Chromium tanpa layar. Mereka tidak menggantikan uji di ponsel sungguhan: notifikasi saat layar terkunci, membuka `.ics` di aplikasi Kalender, dialog pasang, pembaca layar (TalkBack atau VoiceOver), dan Safari di iPhone tidak tercakup.
- Izin notifikasi, getaran, dan status "tersembunyi" disimulasikan.
- Jika kamu mengubah teks atau struktur aplikasi, sebagian tes bisa perlu disesuaikan. Itu tanda tes bekerja, bukan otomatis bug.
