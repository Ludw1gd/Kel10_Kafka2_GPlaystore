# spark_training.py (Menggunakan Category untuk FP-Growth)

from pyspark.sql import SparkSession
# Import fungsi size
from pyspark.sql.functions import col, regexp_replace, when, avg, split, array, size
from pyspark.ml.feature import VectorAssembler, StandardScaler, PCA
from pyspark.ml.clustering import KMeans
from pyspark.ml.fpm import FPGrowth
from pyspark.ml import Pipeline
import os
import shutil

# Inisialisasi Spark Session
spark = SparkSession.builder \
    .appName("PlaystoreMLTraining") \
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
if len(batch_files) < 3:
    print("Jumlah file batch kurang dari 3. Tidak bisa melatih 3 model kumulatif.")
    spark.stop()
    exit()

model_configs = [
    {'name': 'model1', 'files': batch_files[:1]}, # Batch 1
    {'name': 'model2', 'files': batch_files[:2]}, # Batch 1 + Batch 2
    {'name': 'model3', 'files': batch_files}      # Semua Batch
]

# Kolom fitur numerik
numeric_features = ['Rating', 'Reviews', 'Size', 'Installs', 'Price']
# Kolom yang akan digunakan untuk FP-Growth (Sekarang menggunakan Category)
fpgrowth_item_col = 'Category' # <-- UBAH DARI 'Genres' MENJADI 'Category'

# Pra-pemrosesan dan Training Loop
for config in model_configs:
    model_suffix = config['name']
    files_to_process = config['files']

    print(f"\n--- Memulai training for models {model_suffix} using files: {files_to_process} ---")

    # Baca data dari file batch
    # Spark akan menginferensi skema dari file CSV
    df = spark.read.csv(files_to_process, header=True, inferSchema=True)
    print(f"Jumlah baris setelah membaca file: {df.count()}")
    print("Schema of loaded DataFrame:")
    df.printSchema() # <-- Tambahkan ini untuk verifikasi kolom

    # --- Pra-pemrosesan Data (Sama untuk semua model) ---

    # 1. Bersihkan dan Konversi Kolom Numerik
    df = df.withColumn("Reviews", col("Reviews").cast("double"))
    df = df.withColumn("Rating", col("Rating").cast("double"))
    df = df.withColumn("Installs", regexp_replace(col("Installs"), "\\+", ""))
    df = df.withColumn("Installs", regexp_replace(col("Installs"), ",", ""))
    df = df.withColumn("Installs", col("Installs").cast("double"))
    df = df.withColumn("Size",
                       when(col("Size").endswith("M"), regexp_replace(col("Size"), "M", "").cast("double"))
                       .when(col("Size").endswith("k"), (regexp_replace(col("Size"), "k", "").cast("double") / 1024))
                       .otherwise(None))
    df = df.withColumn("Price", regexp_replace(col("Price"), "\\$", ""))
    df = df.withColumn("Price", col("Price").cast("double"))

    # 2. Hitung nilai pengisi (misal: rata-rata Rating)
    avg_rating_row = df.agg(avg(col("Rating"))).collect()[0]
    avg_rating = avg_rating_row[0] if avg_rating_row and avg_rating_row[0] is not None else 0.0

    # 3. Isi nilai null menggunakan .na.fill() pada DataFrame
    fill_values = {
        'Rating': avg_rating,
        'Reviews': 0.0,
        'Size': 0.0,
        'Installs': 0.0,
        'Price': 0.0
    }
    df = df.na.fill(fill_values, subset=numeric_features)

    # Handle missing values di kolom Category (penting untuk FP-Growth)
    df = df.na.fill('Unknown', subset=[fpgrowth_item_col]) # Menggunakan fpgrowth_item_col = 'Category'

    # Drop baris jika masih ada null di kolom fitur numerik atau Category setelah fill
    df = df.na.drop(subset=numeric_features + [fpgrowth_item_col])


    rows_after_preprocessing = df.count()
    print(f"Jumlah baris setelah pra-pemrosesan dan na.fill: {rows_after_preprocessing}")

    # Pastikan ada data untuk dilatih
    if rows_after_preprocessing == 0:
        print(f"Tidak ada data untuk melatih models {model_suffix}. Skipping training.")
        continue

    # --- K-Means Pipeline ---
    print(f"Defining K-Means pipeline for {model_suffix}...")
    kmeans_features = numeric_features
    kmeans_assembler = VectorAssembler(inputCols=kmeans_features, outputCol="features_kmeans")
    kmeans_scaler = StandardScaler(inputCol="features_kmeans", outputCol="scaledFeatures_kmeans", withStd=True, withMean=False)
    kmeans_model = KMeans().setFeaturesCol("scaledFeatures_kmeans").setPredictionCol("prediction_kmeans").setK(10).setSeed(1)

    kmeans_pipeline = Pipeline(stages=[kmeans_assembler, kmeans_scaler, kmeans_model])

    # --- PCA Pipeline ---
    print(f"Defining PCA pipeline for {model_suffix}...")
    pca_features = numeric_features
    pca_assembler = VectorAssembler(inputCols=pca_features, outputCol="features_pca")
    pca_scaler = StandardScaler(inputCol="features_pca", outputCol="scaledFeatures_pca", withStd=True, withMean=False)
    pca_model = PCA().setInputCol("scaledFeatures_pca").setOutputCol("pcaFeatures").setK(3)

    pca_pipeline = Pipeline(stages=[pca_assembler, pca_scaler, pca_model])

    # --- FP-Growth Estimator ---
    print(f"Defining FP-Growth estimator for {model_suffix}...")
    # Pra-pemrosesan spesifik untuk FP-Growth: Buat array dari kolom Category
    df_fpgrowth = df.withColumn("category_array", array(col(fpgrowth_item_col)))

    # Filter out null or empty arrays
    # PERBAIKI DI SINI: Gunakan fungsi size() dari pyspark.sql.functions
    df_fpgrowth = df_fpgrowth.filter(col("category_array").isNotNull() & (size(col("category_array")) > 0))

    # FP-Growth estimator
    fpgrowth_estimator = FPGrowth(itemsCol="category_array", minSupport=0.005, minConfidence=0.5)


    # --- Latih dan Simpan Models ---

    # Latih dan Simpan K-Means Model
    kmeans_model_output_path = os.path.join(MODEL_BASE_DIR, f'kmeans_{model_suffix}')
    print(f"Melatih model K-Means ({model_suffix})...")
    kmeans_model_fitted = kmeans_pipeline.fit(df)
    print(f"Model K-Means {model_suffix} selesai dilatih.")
    print(f"Menyimpan model K-Means {model_suffix} ke {kmeans_model_output_path}...")
    if os.path.exists(kmeans_model_output_path): shutil.rmtree(kmeans_model_output_path)
    kmeans_model_fitted.save(kmeans_model_output_path)
    print(f"Model K-Means {model_suffix} berhasil disimpan.")

    # Latih dan Simpan PCA Model
    pca_model_output_path = os.path.join(MODEL_BASE_DIR, f'pca_{model_suffix}')
    print(f"Melatih model PCA ({model_suffix})...")
    pca_model_fitted = pca_pipeline.fit(df)
    print(f"Model PCA {model_suffix} selesai dilatih.")
    print(f"Menyimpan model PCA {model_suffix} ke {pca_model_output_path}...")
    if os.path.exists(pca_model_output_path): shutil.rmtree(pca_model_output_path)
    pca_model_fitted.save(pca_model_output_path)
    print(f"Model PCA {model_suffix} berhasil disimpan.")

    # Latih dan Simpan FP-Growth Model
    fpgrowth_model_output_path = os.path.join(MODEL_BASE_DIR, f'fpgrowth_results_{model_suffix}')
    print(f"Melatih model FP-Growth ({model_suffix})...")
    # Latih FP-Growth pada DataFrame yang sudah diproses untuk FP-Growth (dengan kolom array category)
    # Pastikan df_fpgrowth tidak kosong sebelum fit
    if df_fpgrowth.count() > 0: # Tambahkan cek count lagi di sini khusus untuk df_fpgrowth
        fpgrowth_model_fitted = fpgrowth_estimator.fit(df_fpgrowth)
        print(f"Model FP-Growth {model_suffix} selesai dilatih.")

        # Simpan Frequent Itemsets sebagai Parquet
        frequent_itemsets = fpgrowth_model_fitted.freqItemsets
        print(f"Menyimpan Frequent Itemsets FP-Growth {model_suffix} ke {fpgrowth_model_output_path}...")
        if os.path.exists(fpgrowth_model_output_path): shutil.rmtree(fpgrowth_model_output_path)
        frequent_itemsets.write.parquet(fpgrowth_model_output_path)
        print(f"Frequent Itemsets FP-Growth {model_suffix} berhasil disimpan.")
    else:
        print(f"Tidak ada data valid untuk melatih model FP-Growth {model_suffix} setelah filtering. Melewati training.")

print("\nAll models finished training and saving (if data was available).")

# Stop Spark Session
spark.stop()