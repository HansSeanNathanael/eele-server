# EELE SERVER

Ikuti petunjuk pengaturan device Tuya pada [TinyTuya](https://github.com/jasonacox/tinytuya)


Jalankan instruksi di bawah untuk install semua dependency

```python
pip install -r requirements. txt
```


Kemudian ambil Device ID, IP ADDRESS, dan LOCAL KEY perangkat Tuya dari file ```devices.json``` yang berasal dari

```
python -m tinytuya wizard
```

Masukkan data tersebut ke dalam saved_plug serta perbarui id plug pada room dengan Device ID yang sudah didapatkan.


Ambil ip address dari android yang digunakan sebagai kamera dan masukkan ke dalam saved_camera dengan format

```
ws://IP_ADDRESS:7711
```

Kemudian perbarui address pada room.