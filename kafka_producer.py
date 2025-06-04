from kafka import KafkaProducer
import time
import random
import csv
import io

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
            # Gabungkan kolom kembali menjadi string CSV.
            # csv.writer akan menangani quoting jika ada koma di dalam data.
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(row) # Tulis list of strings (row)
            message = output.getvalue().strip() # Ambil string dan hapus newline di akhir

            # Kirim pesan ke Kafka
            producer.send(KAFKA_TOPIC, value=message)
            # print(f"Mengirim baris {i+1}: {message[:80]}...") # Print sebagian pesan (opsional, bisa memperlambat)

            # Tambahkan jeda random yang SANGAT KECIL
            # Ini mensimulasikan streaming cepat
            sleep_time = random.uniform(0.001, 0.005) # Jeda antara 1 hingga 5 milidetik
            time.sleep(sleep_time)

    print("Selesai membaca dataset dan mengirim pesan.")

except FileNotFoundError:
    print(f"Error: File dataset '{DATASET_FILE}' tidak ditemukan.")
except Exception as e:
    print(f"Terjadi kesalahan: {e}")
    import traceback
    traceback.print_exc()
finally:
    producer.close()
    print("Kafka Producer ditutup.")