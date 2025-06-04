from kafka import KafkaConsumer
import json
import os
import time
from datetime import datetime
import csv
import io
import traceback

# Konfigurasi Kafka
KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'playstore_apps'
BATCH_DIR = './data_batches'
BATCH_SIZE = 100000 # Simpan setiap 100.000 baris

# Pastikan direktori batch ada
os.makedirs(BATCH_DIR, exist_ok=True)

# Header CSV untuk file batch (sesuai dengan kolom yang dipilih)
CSV_HEADER = ["App","Category","Rating","Reviews","Size","Installs","Type","Price","Content Rating","Last Updated","Android Ver"]

# Indeks kolom yang dibutuhkan dari file CSV original (24 kolom)
# Dalam urutan yang diinginkan untuk file batch (13 kolom)
# Berdasarkan analisis sebelumnya: [0, 2, 3, 4, 11, 5, 8, 9, 18, 10, 17, 16, 12]
COL_INDICES = [0, 2, 3, 4, 11, 5, 8, 9, 18, 17, 12]
EXPECTED_ORIGINAL_COLS = 24 # Jumlah kolom di file CSV original

# Inisialisasi Consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset='earliest', # Mulai baca dari awal jika belum ada offset
    enable_auto_commit=True,
    group_id='playstore-consumer-group', # Group ID untuk menyimpan offset
    value_deserializer=lambda x: x.decode('utf-8')
)

print(f"Kafka Consumer terhubung ke {KAFKA_BROKER} dan berlangganan topik {KAFKA_TOPIC}")
print(f"Menyimpan batch di: {BATCH_DIR}")

# Buffer akan menyimpan list of list (setiap inner list adalah baris dengan 13 kolom)
message_buffer = []
batch_count = 0

try:
    for message in consumer:
        # message.value berisi string satu baris dari CSV original (24 kolom)
        raw_line = message.value

        # Gunakan modul csv untuk mem-parsing baris mentah
        f = io.StringIO(raw_line)
        reader = csv.reader(f)
        try:
            original_row_fields = next(reader) # Parse baris menjadi list of strings
        except Exception as e:
            print(f"Gagal mem-parsing baris: {raw_line[:100]}... Error: {e}")
            continue # Lewati baris yang gagal diparse

        # Pastikan jumlah kolom sesuai harapan (24 kolom di original)
        if len(original_row_fields) != EXPECTED_ORIGINAL_COLS:
            print(f"Peringatan: Baris memiliki jumlah kolom yang tidak sesuai ({len(original_row_fields)} bukan {EXPECTED_ORIGINAL_COLS}): {raw_line[:100]}...")
            # Lewati baris yang jumlah kolomnya salah
            continue

        # Pilih kolom yang dibutuhkan berdasarkan indeks
        try:
            selected_fields = [original_row_fields[i] for i in COL_INDICES]
        except IndexError:
             print(f"Peringatan: Gagal memilih kolom menggunakan indeks. Baris mungkin terlalu pendek: {raw_line[:100]}...")
             continue # Lewati jika indeks di luar batas

        # Tambahkan list of strings (13 kolom) ke buffer
        message_buffer.append(selected_fields)

        # Cek apakah buffer sudah mencapai ukuran batch
        if len(message_buffer) >= BATCH_SIZE:
            batch_count += 1
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            batch_filename = os.path.join(BATCH_DIR, f'batch_{batch_count}_{timestamp}.csv')

            print(f"Menyimpan Batch {batch_count} ({len(message_buffer)} baris) ke {batch_filename}")

            # Tulis batch ke file CSV
            with open(batch_filename, mode='w', encoding='utf-8', newline='') as f: # newline='' penting untuk csv.writer
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER) # Tulis header
                writer.writerows(message_buffer) # Tulis semua baris dari buffer (list of list)

            # Kosongkan buffer setelah disimpan
            message_buffer = []
            print(f"Batch {batch_count} berhasil disimpan.")

except KeyboardInterrupt:
    print("Consumer dihentikan secara manual.")
except Exception as e:
    print(f"Terjadi kesalahan: {e}")
    traceback.print_exc()
finally:
    # Simpan sisa data di buffer saat consumer berhenti
    if message_buffer:
        batch_count += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_remaining")
        batch_filename = os.path.join(BATCH_DIR, f'batch_{batch_count}_{timestamp}.csv')
        print(f"Menyimpan sisa Batch {batch_count} ({len(message_buffer)} baris) ke {batch_filename}")
        with open(batch_filename, mode='w', encoding='utf-8', newline='') as f:
             writer = csv.writer(f)
             writer.writerow(CSV_HEADER) # Tulis header
             writer.writerows(message_buffer) # Tulis semua baris dari buffer
        print(f"Sisa Batch {batch_count} berhasil disimpan.")
    consumer.close()
    print("Kafka Consumer ditutup.")