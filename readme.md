# Kel10_Kafka2_GPlaystore

## Anggota Tim

| Nama             | NRP        |
|------------------|------------|
| Dionisius Marcel | 5027231044 |
| Muhammad Nafi    | 5027231045 |
| Tio Axellino     | 5027231065 |

Proyek ini mensimulasikan arsitektur sistem Big Data sederhana untuk pemrosesan data stream menggunakan Apache Kafka dan Apache Spark. Data stream disimulasikan dari dataset Google Playstore, diproses dalam batch, digunakan untuk melatih **beberapa model Machine Learning (Clustering, Dimensionality Reduction)** dan melakukan analisis **Association Rule Mining** menggunakan Spark, dan model serta hasil analisis tersebut disajikan melalui API.

## Struktur Proyek

    .
    ├── docker-compose.yml      # Konfigurasi Docker untuk Kafka & Zookeeper
    ├── .gitignore              # File yang diabaikan oleh Git
    ├── .gitattributes          # Konfigurasi Git LFS (jika digunakan) atau filter-repo
    ├── kafka_producer.py       # Script untuk mengirim data dari CSV ke Kafka
    ├── kafka_consumer.py       # Script untuk membaca dari Kafka dan menyimpan batch
    ├── spark_training.py       # Script PySpark untuk pra-pemrosesan dan training model/analisis
    ├── api_server.py           # Script Flask untuk menyajikan model/hasil melalui API
    ├── README.md               # File ini
    ├── Google-Playstore.csv    # **Dataset (Harus diunduh secara terpisah)**
    ├── data_batches/           # Direktori output Kafka Consumer (dibuat saat runtime)
    │   └── batch_1_timestamp.csv
    │   └── batch_2_timestamp.csv
    │   └── ...
    └── trained_models/         # Direktori output Spark Training (dibuat saat runtime)
        └── kmeans_model1/      # Model K-Means dari batch 1
        └── kmeans_model2/      # Model K-Means dari batch 1+2
        └── kmeans_model3/      # Model K-Means dari semua batch
        └── pca_model1/         # Model PCA dari batch 1
        └── pca_model2/         # Model PCA dari batch 1+2
        └── pca_model3/         # Model PCA dari semua batch
        └── fpgrowth_results_model1/ # Hasil FP-Growth dari batch 1 (Frequent Itemsets - Parquet)
        └── fpgrowth_results_model2/ # Hasil FP-Growth dari batch 1+2
        └── fpgrowth_results_model3/ # Hasil FP-Growth dari semua batch

## Fitur Utama

*   Simulasi data stream dari file CSV menggunakan Kafka Producer.
*   Batching data stream yang diterima menggunakan Kafka Consumer.
*   Pelatihan beberapa model **K-Means Clustering**, **PCA (Principal Component Analysis)**, dan analisis **FP-Growth (Frequent Pattern Mining)** menggunakan Apache Spark MLlib pada subset data yang berbeda (kumulatif batch).
*   Penyajian model dan hasil analisis yang telah dilatih melalui REST API menggunakan Flask.

## Arsitektur Sistem

Sistem ini mengikuti alur berikut:

`Google-Playstore.csv` (File) -> Kafka Producer (Python) -> Kafka Server (Docker) -> Kafka Consumer (Python) -> Data Batches (Files) -> Spark Script (PySpark) -> Trained Models/Results (Files) -> API Server (Python/Flask) -> User Request

## Prasyarat

Pastikan Anda telah menginstal perangkat lunak berikut di sistem Anda:

*   **Docker & Docker Compose:** Untuk menjalankan Kafka Server dan API Server.
    *   [Instal Docker Engine](https://docs.docker.com/engine/install/)
    *   [Instal Docker Compose](https://docs.docker.com/compose/install/)
*   **Python 3.11:** Untuk menjalankan Producer, Consumer, dan script Spark (jika tidak menggunakan `spark-submit` dengan distribusi Spark lengkap).
    *   [Unduh Python](https://www.python.org/downloads/)
*   **Java:** Diperlukan oleh Apache Spark (baik di host untuk `spark-submit` maupun di dalam kontainer Docker untuk API). Versi Java 8, 11, atau 17 direkomendasikan untuk Spark 3.5.5.
    *   [Unduh Java (OpenJDK direkomendasikan)](https://openjdk.java.net/install/)
*   **Apache Spark:** Diperlukan untuk menjalankan script training model. Anda bisa mengunduh distribusi Spark dan mengatur variabel lingkungan `SPARK_HOME` (terutama jika menjalankan `spark_training.py` di host), atau memastikan PySpark terinstal di lingkungan Python Anda (diperlukan di host dan di dalam kontainer API).
    *   [Unduh Apache Spark](https://spark.apache.org/downloads.html)
    *   [Instal PySpark (jika tidak menggunakan distribusi Spark lengkap)](https://spark.apache.org/docs/latest/api/python/getting_started/install.html)
*   **Hadoop Binary untuk Windows (Jika menjalankan Spark di Host Windows):** Jika Anda menjalankan `spark_training.py` langsung di host Windows, Anda memerlukan `winutils.exe` yang kompatibel dengan versi Hadoop Spark Anda (Hadoop 3.3.6 untuk Spark 3.5.5) dan mengatur variabel lingkungan `HADOOP_HOME`. (Ini tidak diperlukan jika menjalankan Spark Training di Docker).

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
    pip install -r requirements.txt
    ```
    *(Pastikan file `requirements.txt` ada dan berisi `pyspark==3.5.5`, `flask`, `kafka-python`, `pandas`.)*
    *(Catatan: `pyspark` mungkin sudah tersedia jika Anda menggunakan distribusi Spark lengkap dan mengatur `SPARK_HOME`.)*

4.  **Setup Kafka Server (menggunakan Docker):**
    Pastikan Docker Desktop berjalan. Di root directory proyek, jalankan:
    ```bash
    docker-compose up -d zookeeper kafka
    ```
    Ini akan memulai kontainer Zookeeper dan Kafka di background. Tunggu beberapa saat hingga keduanya siap.

5.  **Buat Topik Kafka:**
    Anda perlu membuat topik di Kafka tempat producer akan mengirim data.
    *   Temukan nama kontainer Kafka Anda (misal: `kel10_kafka2_gplaystore_kafka_1` atau `tugaskafka2-kafka-1`) dengan `docker ps`.
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
    Script ini akan membaca file-file batch dari `./data_batches`, melakukan pra-pemrosesan, melatih **3 model K-Means, 3 model PCA, dan menghitung Frequent Itemsets FP-Growth** pada subset data kumulatif, dan menyimpannya di direktori `./trained_models`.
    ```bash
    # Pastikan virtual environment aktif dan SPARK_HOME diatur, atau PySpark terinstal
    spark-submit spark_training.py
    ```
    Tunggu hingga script ini selesai berjalan. Anda akan melihat pesan konfirmasi untuk setiap model/hasil yang dilatih dan disimpan.

4.  **Bangun dan Jalankan API Server (menggunakan Docker):**
    Pastikan Docker Desktop berjalan. Di root directory proyek, bangun image Docker untuk API server, lalu jalankan kontainernya.
    ```bash
    docker-compose build api-server
    docker-compose up -d api-server
    ```
    API akan berjalan di `http://localhost:5000`. Periksa log kontainer API (`docker logs <nama_kontainer_api>`) untuk memastikan semua model/hasil berhasil dimuat saat startup.

## Menguji API

API menyediakan tiga jenis endpoint berbeda untuk mendapatkan hasil dari model/analisis yang telah dilatih: Clustering (K-Means), Dimensionality Reduction (PCA), dan Frequent Itemsets (FP-Growth).

**Endpoint 1: Prediksi Clustering (K-Means)**

*   **URL:** `POST http://localhost:5000/cluster/<model_suffix>`
*   **Metode:** `POST`
*   **Deskripsi:** Mengembalikan ID cluster yang diprediksi oleh model K-Means yang dipilih untuk input fitur aplikasi.
*   **`model_suffix`:** `model1`, `model2`, atau `model3` (sesuai dengan batch data yang digunakan saat training).
*   **Body Request (JSON):** Fitur numerik aplikasi. Nama kolom harus sesuai dengan `NUMERIC_FEATURES` (`Rating`, `Reviews`, `Size`, `Installs`, `Price`). Nilai harus numerik (float/int).
    ```json
    {
      "Rating": 4.5,
      "Reviews": 1500000.0,
      "Size": 30.5,       // dalam MB
      "Installs": 50000000.0,
      "Price": 0.0
    }
    ```
*   **Contoh Menggunakan `curl`:**
    ```bash
    curl -X POST \
      http://localhost:5000/cluster/model1 \
      -H 'Content-Type: application/json' \
      -d '{
        "Rating": 4.5,
        "Reviews": 1500000.0,
        "Size": 30.5,
        "Installs": 50000000.0,
        "Price": 0.0
      }'
    ```
*   **Contoh Response (JSON):**
    ```json
    {
      "model_used": "kmeans_model1",
      "input_features": {
        "Rating": 4.5,
        "Reviews": 1500000.0,
        "Size": 30.5,
        "Installs": 50000000.0,
        "Price": 0.0
      },
      "predicted_cluster_id": 1
    }
    ```

**Endpoint 2: Transformasi PCA**

*   **URL:** `POST http://localhost:5000/transform_pca/<model_suffix>`
*   **Metode:** `POST`
*   **Deskripsi:** Mengembalikan vektor fitur aplikasi setelah direduksi dimensinya menggunakan model PCA yang dipilih.
*   **`model_suffix`:** `model1`, `model2`, atau `model3`.
*   **Body Request (JSON):** Fitur numerik aplikasi (sama seperti input Clustering).
    ```json
    {
      "Rating": 4.2,
      "Reviews": 50000.0,
      "Size": 25.0,
      "Installs": 500000.0,
      "Price": 0.0
    }
    ```
*   **Contoh Menggunakan `curl`:**
    ```bash
    curl -X POST \
      http://localhost:5000/transform_pca/model2 \
      -H 'Content-Type: application/json' \
      -d '{
        "Rating": 4.2,
        "Reviews": 50000.0,
        "Size": 25.0,
        "Installs": 500000.0,
        "Price": 0.0
      }'
    ```
*   **Contoh Response (JSON):**
    ```json
    {
      "model_used": "pca_model2",
      "input_features": {
        "Rating": 4.2,
        "Reviews": 50000.0,
        "Size": 25.0,
        "Installs": 500000.0,
        "Price": 0.0
      },
      "transformed_pca_features": [
        -0.4726048133747775,
        2.1500865639549587,
        0.054155173548551885
      ]
    }
    ```

**Endpoint 3: Frequent Itemsets (FP-Growth)**

*   **URL:** `GET http://localhost:5000/frequent_itemsets/<model_suffix>`
*   **Metode:** `GET`
*   **Deskripsi:** Mengembalikan daftar itemset (kategori aplikasi) yang sering muncul bersamaan, berdasarkan hasil analisis FP-Growth yang dipilih.
*   **`model_suffix`:** `model1`, `model2`, atau `model3`.
*   **Body Request:** Tidak diperlukan untuk metode GET.
*   **Contoh Menggunakan `curl`:**
    ```bash
    curl http://localhost:5000/frequent_itemsets/model3
    ```
*   **Contoh Response (JSON):**
    ```json
    {
      "results_used": "fpgrowth_results_model3",
      "frequent_itemsets": [
        { "items": ["FAMILY"], "freq": 50000 },
        { "items": ["GAME"], "freq": 45000 },
        { "items": ["TOOLS"], "freq": 30000 },
        { "items": ["GAME", "FAMILY"], "freq": 10000 },
        { "items": ["COMMUNICATION"], "freq": 8000 },
        { "items": ["GAME", "TOOLS"], "freq": 5000 }
        // ... daftar itemset dan frekuensi lainnya
      ]
    }
    ```
