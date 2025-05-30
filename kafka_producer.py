from kafka import KafkaProducer
import time
import random
import csv

# Konfigurasi Kafka
KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'playstore_apps'
DATASET_FILE = 'Google-Playstore.csv' # Pastikan file ini ada di lokasi yang sama

# Inisialisasi Producer
producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER,
                         value_serializer=lambda x: x.encode('utf-8'))

print(f"Kafka Producer terhubung ke {KAFKA_BROKER}")

try:
    with open(DATASET_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        header = next(reader) # Baca dan lewati header

        print(f"Mulai membaca dataset: {DATASET_FILE}")
        for i, row in enumerate(reader):
            # Gabungkan kolom menjadi string CSV kembali
            # Hati-hati dengan koma di dalam data, mungkin perlu quoting
            # Cara paling aman adalah mengirim baris asli sebagai string
            message = ','.join(row) # Ini mungkin perlu disesuaikan tergantung format CSV

            # Kirim pesan ke Kafka
            producer.send(KAFKA_TOPIC, value=message)
            print(f"Mengirim baris {i+1}: {message[:50]}...") # Print sebagian pesan
            
            # Tambahkan jeda random
            sleep_time = random.uniform(0.001, 0.01) # Jeda antara 0.1 hingga 0.5 detik
            time.sleep(sleep_time)

    print("Selesai membaca dataset dan mengirim pesan.")

except FileNotFoundError:
    print(f"Error: File dataset '{DATASET_FILE}' tidak ditemukan.")
except Exception as e:
    print(f"Terjadi kesalahan: {e}")
finally:
    producer.close()
    print("Kafka Producer ditutup.")