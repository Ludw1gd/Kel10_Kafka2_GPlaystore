# Kel10_Kafka2_GPlaystore

## Anggota Tim

| Nama             | NRP        |
|------------------|------------|
| Dionisius Marcel |            |
| Muhammad Nafi    | 5027231045 |
| Tio Axellino     | 5027231065 |

Proyek ini mensimulasikan arsitektur sistem Big Data sederhana untuk pemrosesan data stream menggunakan Apache Kafka dan Apache Spark. Data stream disimulasikan dari dataset Google Playstore, diproses dalam batch, digunakan untuk melatih beberapa model Machine Learning (Clustering) menggunakan Spark, dan model-model tersebut disajikan melalui API.

## Struktur Proyek

    .
    ├── docker-compose.yml      # Konfigurasi Docker untuk Kafka & Zookeeper
    ├── .gitignore              # File yang diabaikan oleh Git
    ├── .gitattributes          # Konfigurasi Git LFS (jika digunakan) atau filter-repo
    ├── kafka_producer.py       # Script untuk mengirim data dari CSV ke Kafka
    ├── kafka_consumer.py       # Script untuk membaca dari Kafka dan menyimpan batch
    ├── spark_training.py       # Script PySpark untuk pra-pemrosesan dan training model
    ├── api_server.py           # Script Flask untuk menyajikan model melalui API
    ├── README.md               # File ini
    ├── Google-Playstore.csv    # **Dataset (Harus diunduh secara terpisah)**
    ├── data_batches/           # Direktori output Kafka Consumer (dibuat saat runtime)
    │   └── batch_1_timestamp.csv
    │   └── batch_2_timestamp.csv
    │   └── ...
    └── trained_models/         # Direktori output Spark Training (dibuat saat runtime)
        └── model1/             # Model K-Means dari batch 1
        └── model2/             # Model K-Means dari batch 1+2
        └── model3/             # Model K-Means dari semua batch

## Fitur Utama

*   Simulasi data stream dari file CSV menggunakan Kafka Producer.
*   Batching data stream yang diterima menggunakan Kafka Consumer.
*   Pelatihan beberapa model K-Means Clustering menggunakan Apache Spark MLlib pada subset data yang berbeda (kumulatif batch).
*   Penyajian model K-Means yang telah dilatih melalui REST API menggunakan Flask.

## Arsitektur Sistem

Sistem ini mengikuti alur berikut:

`Google-Playstore.csv` (File) -> Kafka Producer (Python) -> Kafka Server (Docker) -> Kafka Consumer (Python) -> Data Batches (Files) -> Spark Script (PySpark) -> Trained Models (Files) -> API Server (Python/Flask) -> User Request

## Prasyarat

Pastikan Anda telah menginstal perangkat lunak berikut di sistem Anda:

*   **Docker & Docker Compose:** Untuk menjalankan Kafka Server.
    *   [Instal Docker Engine](https://docs.docker.com/engine/install/)
    *   [Instal Docker Compose](https://docs.docker.com/compose/install/)
*   **Python 3.11:** Untuk menjalankan Producer, Consumer, dan API.
    *   [Unduh Python](https://www.python.org/downloads/)
*   **Java:** Diperlukan oleh Apache Spark.
    *   [Unduh Java (OpenJDK direkomendasikan)](https://openjdk.java.net/install/)
*   **Apache Spark:** Diperlukan untuk menjalankan script training model. Anda bisa mengunduh distribusi Spark dan mengatur variabel lingkungan `SPARK_HOME`, atau memastikan PySpark terinstal di lingkungan Python Anda.
    *   [Unduh Apache Spark](https://spark.apache.org/downloads.html)
    *   [Instal PySpark (jika tidak menggunakan distribusi Spark lengkap)](https://spark.apache.org/docs/latest/api/python/getting_started/install.html)

## Setup Proyek

Ikuti langkah-langkah berikut untuk menyiapkan proyek di lingkungan lokal Anda:

1.  **Clone Repository:**
    ```bash
    git clone https://github.com/Ludw1gd/Kel10_Kafka2_GPlaystore.git
    cd Kel10_Kafka2_GPlaystore
    ```

2.  **Unduh Dataset:**
    Dataset `Google-Playstore.csv` **tidak disertakan dalam repository ini** karena ukurannya yang besar. Anda harus mengunduhnya secara terpisah.
    *   Cari dataset "Google Play Store Apps" di platform seperti Kaggle.
    *   Unduh file `Google-Playstore.csv`.
    *   Letakkan file `Google-Playstore.csv` yang telah diunduh di **root directory** proyek ini (di direktori `Kel10_Kafka2_GPlaystore`).

3.  **Setup Lingkungan Python:**
    Disarankan untuk menggunakan virtual environment.
    ```bash
    python -m venv .venv
    # Aktifkan virtual environment
    # Di Windows:
    # .venv\Scripts\activate
    # Di macOS/Linux:
    # source .venv/bin/activate
    ```
    Instal library Python yang diperlukan:
    ```bash
    pip install kafka-python pandas flask pyspark
    ```
    *(Catatan: `pyspark` mungkin sudah tersedia jika Anda menggunakan distribusi Spark lengkap dan mengatur `SPARK_HOME`.)*

4.  **Setup Kafka Server (menggunakan Docker):**
    Pastikan Docker Desktop berjalan. Di root directory proyek, jalankan:
    ```bash
    docker-compose up -d
    ```
    Ini akan memulai kontainer Zookeeper dan Kafka di background. Tunggu beberapa saat hingga keduanya siap.

5.  **Buat Topik Kafka:**
    Anda perlu membuat topik di Kafka tempat producer akan mengirim data.
    *   Temukan nama kontainer Kafka Anda (misal: `kel10_kafka2_gplaystore_kafka_1`) dengan `docker ps`.
    *   Jalankan perintah berikut di terminal (ganti `<nama_container_kafka>`):
    ```bash
    docker exec -it <nama_container_kafka> bash
    kafka-topics --create --topic playstore_apps --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
    exit
    ```
    Topik `playstore_apps` sekarang siap.

## Menjalankan Sistem

Jalankan komponen sistem secara berurutan:

1.  **Jalankan Kafka Producer:**
    Script ini akan membaca `Google-Playstore.csv` baris per baris dan mengirimkannya ke Kafka.
    ```bash
    # Pastikan virtual environment aktif
    python kafka_producer.py
    ```
    *(Catatan: Script ini memiliki jeda random antar pengiriman baris untuk mensimulasikan streaming. Untuk pengujian cepat, Anda bisa mengurangi nilai jeda (`time.sleep`) di dalam `kafka_producer.py`.)*
    Biarkan script ini berjalan hingga selesai membaca seluruh file atau sampai Anda menghentikannya secara manual setelah mengirim cukup data (misal: > 300.000 baris untuk melatih 3 model dengan batch size 100.000).

2.  **Jalankan Kafka Consumer:**
    Script ini akan membaca data dari Kafka dan menyimpannya dalam batch-batch file CSV di direktori `./data_batches`.
    ```bash
    # Pastikan virtual environment aktif
    python kafka_consumer.py
    ```
    Biarkan script ini berjalan *bersamaan* dengan Producer. Anda akan melihat pesan di terminal setiap kali satu batch selesai disimpan. Hentikan Consumer (Ctrl+C) setelah Producer selesai mengirim data dan Consumer telah memproses semua pesan yang terkirim (atau setelah Anda yakin sudah ada cukup file batch, minimal 3 file batch untuk melatih 3 model kumulatif).

3.  **Jalankan Spark Training Script:**
    Script ini akan membaca file-file batch dari `./data_batches`, melakukan pra-pemrosesan, melatih 3 model K-Means pada subset data kumulatif, dan menyimpannya di direktori `./trained_models`.
    ```bash
    # Pastikan virtual environment aktif dan SPARK_HOME diatur, atau PySpark terinstal
    spark-submit spark_training.py
    ```
    Tunggu hingga script ini selesai berjalan. Anda akan melihat pesan konfirmasi untuk setiap model yang dilatih dan disimpan.

4.  **Jalankan API Server:**
    Script ini akan memuat model-model yang telah dilatih oleh Spark dan menjalankan server API menggunakan Flask.
    ```bash
    # Pastikan virtual environment aktif
    python api_server.py
    ```
    API akan berjalan di `http://localhost:5000`.

## Menguji API

API menyediakan endpoint untuk mendapatkan prediksi cluster dari model K-Means yang berbeda.

**Endpoint:**

*   `POST /cluster/model1`
*   `POST /cluster/model2`
*   `POST /cluster/model3`

**Metode:** `POST`

**Body Request (JSON):**

Anda perlu mengirimkan fitur-fitur numerik dari sebuah aplikasi dalam format JSON. Nama dan urutan fitur harus sesuai dengan yang digunakan saat training model di Spark (`Rating`, `Reviews`, `Size`, `Installs`, `Price`). Pastikan nilai-nilai sudah dalam format numerik yang bersih (setelah pembersihan string seperti '$', '+', ',', 'M', 'k').

```json
{
  "Rating": 4.1,
  "Reviews": 100000.0,
  "Size": 15.0,       // dalam MB
  "Installs": 1000000.0,
  "Price": 0.0
}
```

**Contoh Menggunakan** curl:

```bash
curl -X POST \
  http://localhost:5000/cluster/model1 \
  -H 'Content-Type: application/json' \
  -d '{
    "Rating": 4.1,
    "Reviews": 100000.0,
    "Size": 15.0,
    "Installs": 1000000.0,
    "Price": 0.0
  }'
```

**Contoh Response** (JSON):

```bash
{
  "model_used": "model1",
  "input_features": {
    "Rating": 4.1,
    "Reviews": 100000.0,
    "Size": 15.0,
    "Installs": 1000000.0,
    "Price": 0.0
  },
  "predicted_cluster_id": 5
}
```

