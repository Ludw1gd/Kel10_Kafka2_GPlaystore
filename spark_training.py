# spark_training.py (Perbaikan na.fill)

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, when, avg
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml import Pipeline
import os
import shutil # Import shutil untuk menghapus direktori

# Inisialisasi Spark Session
spark = SparkSession.builder \
    .appName("PlaystoreKMeansTraining") \
    .config("spark.driver.memory", "8g") \
    .getOrCreate()

# Direktori input dan output
BATCH_DIR = './data_batches'
MODEL_BASE_DIR = './trained_models'
os.makedirs(MODEL_BASE_DIR, exist_ok=True)

# Dapatkan daftar file batch dan urutkan
batch_files = sorted([os.path.join(BATCH_DIR, f) for f in os.listdir(BATCH_DIR) if f.endswith('.csv')])
print(f"Ditemukan {len(batch_files)} file batch: {batch_files}")

# Tentukan subset file untuk setiap model (Skema Kumulatif)
# Contoh: 3 model
if len(batch_files) < 3:
    print("Jumlah file batch kurang dari 3. Tidak bisa melatih 3 model kumulatif.")
    spark.stop()
    exit()

model_configs = [
    {'name': 'model1', 'files': batch_files[:1]}, # Batch 1
    {'name': 'model2', 'files': batch_files[:2]}, # Batch 1 + Batch 2
    {'name': 'model3', 'files': batch_files}      # Semua Batch
]

# Pra-pemrosesan dan Training Loop
for config in model_configs:
    model_name = config['name']
    files_to_process = config['files']
    model_output_path = os.path.join(MODEL_BASE_DIR, model_name)

    print(f"\n--- Memulai training untuk {model_name} menggunakan file: {files_to_process} ---")

    # Baca data dari file batch
    df = spark.read.csv(files_to_process, header=True, inferSchema=True)
    print(f"Jumlah baris setelah membaca file: {df.count()}")

    # --- Pra-pemrosesan Data ---

    # 1. Bersihkan dan Konversi Kolom Numerik
    # Lakukan konversi terlebih dahulu
    df = df.withColumn("Reviews", col("Reviews").cast("double"))
    df = df.withColumn("Rating", col("Rating").cast("double"))

    df = df.withColumn("Installs", regexp_replace(col("Installs"), "\\+", ""))
    df = df.withColumn("Installs", regexp_replace(col("Installs"), ",", ""))
    df = df.withColumn("Installs", col("Installs").cast("double"))

    df = df.withColumn("Size",
                       when(col("Size").endswith("M"), regexp_replace(col("Size"), "M", "").cast("double"))
                       .when(col("Size").endswith("k"), (regexp_replace(col("Size"), "k", "").cast("double") / 1024))
                       .otherwise(None)) # Jika format lain, hasilnya None

    df = df.withColumn("Price", regexp_replace(col("Price"), "\\$", ""))
    df = df.withColumn("Price", col("Price").cast("double"))

    # 2. Hitung nilai pengisi (misal: rata-rata Rating)
    # Hitung rata-rata Rating dari data yang tidak null *setelah* konversi
    avg_rating_row = df.agg(avg(col("Rating"))).collect()[0]
    avg_rating = avg_rating_row[0] if avg_rating_row and avg_rating_row[0] is not None else 0.0 # Handle kasus jika semua Rating null

    # 3. Isi nilai null menggunakan .na.fill() pada DataFrame
    fill_values = {
        'Rating': avg_rating,
        'Reviews': 0.0,
        'Size': 0.0,
        'Installs': 0.0,
        'Price': 0.0
    }
    df = df.na.fill(fill_values)

    # Cek jumlah baris setelah pra-pemrosesan (seharusnya sama dengan setelah membaca file)
    rows_after_preprocessing = df.count()
    print(f"Jumlah baris setelah pra-pemrosesan dan na.fill: {rows_after_preprocessing}")

    # Pilih fitur numerik yang akan digunakan untuk clustering
    feature_cols = ['Rating', 'Reviews', 'Size', 'Installs', 'Price']

    # 4. Vector Assembly
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")

    # 5. Scaling Fitur
    scaler = StandardScaler(inputCol="features", outputCol="scaledFeatures",
                            withStd=True, withMean=False)

    # 6. K-Means Model
    # Pilih jumlah cluster (K) - ini bisa jadi parameter tuning
    kmeans = KMeans().setFeaturesCol("scaledFeatures").setPredictionCol("prediction").setK(10).setSeed(1) # Contoh K=10

    # 7. Buat Pipeline
    pipeline = Pipeline(stages=[assembler, scaler, kmeans])

    # --- Latih Model ---
    # Pastikan jumlah baris > 0 sebelum fit
    if rows_after_preprocessing > 0:
        print(f"Melatih model K-Means ({model_name})...")
        model = pipeline.fit(df)
        print(f"Model {model_name} selesai dilatih.")

        # --- Simpan Model ---
        print(f"Menyimpan model {model_name} ke {model_output_path}...")
        # Hapus direktori model lama jika ada, karena save tidak menimpa
        if os.path.exists(model_output_path):
             shutil.rmtree(model_output_path)
        model.save(model_output_path)
        print(f"Model {model_name} berhasil disimpan.")
    else:
        print(f"Tidak ada data untuk melatih model {model_name}. Melewati training.")


print("\nSemua model selesai dilatih dan disimpan (jika ada data).")

# Hentikan Spark Session
spark.stop()