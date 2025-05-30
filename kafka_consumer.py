from kafka import KafkaConsumer
import json
import os
import time
from datetime import datetime

# Konfigurasi Kafka
KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'playstore_apps'
BATCH_DIR = './data_batches'
BATCH_SIZE = 100000 # Simpan setiap 100.000 baris

# Pastikan direktori batch ada
os.makedirs(BATCH_DIR, exist_ok=True)

# Header CSV (sesuai dengan Google-Playstore.csv)
CSV_HEADER = "App,Category,Rating,Reviews,Size,Installs,Type,Price,Content Rating,Genres,Last Updated,Current Ver,Android Ver"

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

message_buffer = []
batch_count = 0

try:
    for message in consumer:
        # message.value berisi string satu baris dari CSV
        line = message.value

        # Tambahkan baris ke buffer
        message_buffer.append(line)

        # Cek apakah buffer sudah mencapai ukuran batch
        if len(message_buffer) >= BATCH_SIZE:
            batch_count += 1
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            batch_filename = os.path.join(BATCH_DIR, f'batch_{batch_count}_{timestamp}.csv')

            print(f"Menyimpan Batch {batch_count} ({len(message_buffer)} baris) ke {batch_filename}")

            with open(batch_filename, mode='w', encoding='utf-8') as f:
                f.write(CSV_HEADER + '\n') # Tulis header
                for msg in message_buffer:
                    f.write(msg + '\n') # Tulis setiap baris dari buffer

            # Kosongkan buffer setelah disimpan
            message_buffer = []
            print(f"Batch {batch_count} berhasil disimpan.")

except KeyboardInterrupt:
    print("Consumer dihentikan secara manual.")
except Exception as e:
    print(f"Terjadi kesalahan: {e}")
finally:
    # Simpan sisa data di buffer saat consumer berhenti
    if message_buffer:
        batch_count += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_remaining")
        batch_filename = os.path.join(BATCH_DIR, f'batch_{batch_count}_{timestamp}.csv')
        print(f"Menyimpan sisa Batch {batch_count} ({len(message_buffer)} baris) ke {batch_filename}")
        with open(batch_filename, mode='w', encoding='utf-8') as f:
             f.write(CSV_HEADER + '\n') # Tulis header
             for msg in message_buffer:
                 f.write(msg + '\n')
        print(f"Sisa Batch {batch_count} berhasil disimpan.")
    consumer.close()
    print("Kafka Consumer ditutup.")