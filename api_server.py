# api_server.py (K-Means, PCA, FP-Growth Endpoints)

from flask import Flask, request, jsonify
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.ml.linalg import Vectors, Vector # Import Vector type
from pyspark.sql.types import StructType, StructField, DoubleType, StringType
from pyspark.sql import Row
import os
import sys
import traceback
import json # Import json for handling FP-Growth results

# --- Konfigurasi PySpark di API ---
# Sesuaikan memory jika perlu
spark = SparkSession.builder \
    .appName("PlaystoreMLAPI") \
    .config("spark.driver.memory", "4g") \
    .master("local[*]") \
    .getOrCreate()

print("Spark Session berhasil diinisialisasi di API.")

app = Flask(__name__)

# Path tempat model dan hasil disimpan di dalam kontainer (sesuai volume mount)
MODEL_BASE_PATH = "/app/trained_models"
loaded_models = {} # Dictionary untuk menyimpan model dan hasil yang dimuat

# Kolom fitur numerik (digunakan oleh K-Means dan PCA)
NUMERIC_FEATURES = ['Rating', 'Reviews', 'Size', 'Installs', 'Price']
# Kolom yang digunakan untuk FP-Growth (Category)
FPGROWTH_ITEM_COL = 'Category'


def load_models():
    """Memuat semua model dan hasil saat API startup."""
    print(f"Mencari model dan hasil di: {MODEL_BASE_PATH}")
    if not os.path.exists(MODEL_BASE_PATH):
        print(f"Direktori model tidak ditemukan: {MODEL_BASE_PATH}")
        return

    # Cari semua sub-direktori model/hasil
    item_dirs = [d for d in os.listdir(MODEL_BASE_PATH) if os.path.isdir(os.path.join(MODEL_BASE_PATH, d))]
    if not item_dirs:
        print("Tidak ada sub-direktori model/hasil ditemukan di MODEL_BASE_PATH.")

    for item_dir_name in item_dirs:
        item_path = os.path.join(MODEL_BASE_PATH, item_dir_name)
        try:
            if item_dir_name.startswith('kmeans_') or item_dir_name.startswith('pca_'):
                # Muat model Pipeline (K-Means atau PCA)
                model = PipelineModel.load(item_path)
                loaded_models[item_dir_name] = model
                print(f"Model '{item_dir_name}' (PipelineModel) berhasil dimuat dari {item_path}")
            elif item_dir_name.startswith('fpgrowth_results_'):
                # Muat hasil FP-Growth (Frequent Itemsets Parquet)
                # Baca Parquet ke DataFrame Spark
                fpgrowth_results_df = spark.read.parquet(item_path)
                loaded_models[item_dir_name] = fpgrowth_results_df
                print(f"Hasil '{item_dir_name}' (FP-Growth Frequent Itemsets) berhasil dimuat dari {item_path}")
            else:
                print(f"Mengabaikan direktori tidak dikenal: {item_dir_name}")

        except Exception as e:
            print(f"Gagal memuat item '{item_dir_name}' dari {item_path}: {e}")
            traceback.print_exc()

with app.app_context():
    load_models()

# --- Endpoint 1: Prediksi Clustering (K-Means) ---
@app.route('/cluster/<model_suffix>', methods=['POST'])
def cluster_predict(model_suffix):
    model_name = f'kmeans_{model_suffix}' # Bentuk nama model lengkap
    if model_name not in loaded_models:
        return jsonify({"error": f"Model '{model_name}' tidak ditemukan"}), 404

    model = loaded_models[model_name]
    data = request.json # Input JSON hanya perlu fitur numerik

    # Validasi input JSON untuk K-Means
    if not data or not all(col in data for col in NUMERIC_FEATURES):
         return jsonify({"error": f"Input JSON harus mengandung semua fitur numerik: {NUMERIC_FEATURES}"}), 400

    try:
        # Ambil nilai fitur numerik dalam urutan yang benar
        feature_values_list = [data[col] for col in NUMERIC_FEATURES]

        # Buat DataFrame dari list of tuples
        input_row_tuple = tuple(feature_values_list)
        # Gunakan NUMERIC_FEATURES sebagai nama kolom
        input_df = spark.createDataFrame([input_row_tuple], NUMERIC_FEATURES)

        # Debugging
        print("\n--- Debugging K-Means Input DataFrame ---")
        input_df.printSchema()
        input_df.show(truncate=False)
        print("--- End Debugging ---\n")

        # Gunakan model Pipeline untuk prediksi cluster
        prediction_df = model.transform(input_df)

        # Ambil hasil prediksi (kolom 'prediction_kmeans' dari pipeline training)
        cluster_id = prediction_df.select("prediction_kmeans").collect()[0][0]

        return jsonify({
            "model_used": model_name,
            "input_features": data,
            "predicted_cluster_id": int(cluster_id)
        })

    except Exception as e:
        print(f"Error saat prediksi clustering: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan saat melakukan prediksi clustering: {e}"}), 500


# --- Endpoint 2: Transformasi PCA ---
@app.route('/transform_pca/<model_suffix>', methods=['POST'])
def transform_pca(model_suffix):
    model_name = f'pca_{model_suffix}' # Bentuk nama model lengkap
    if model_name not in loaded_models:
        return jsonify({"error": f"Model '{model_name}' tidak ditemukan"}), 404

    model = loaded_models[model_name]
    data = request.json # Input JSON perlu fitur numerik

    # Validasi input JSON untuk PCA
    if not data or not all(col in data for col in NUMERIC_FEATURES):
         return jsonify({"error": f"Input JSON harus mengandung semua fitur numerik untuk PCA: {NUMERIC_FEATURES}"}), 400

    try:
        # Ambil nilai fitur numerik dalam urutan yang benar
        feature_values_list = [data[col] for col in NUMERIC_FEATURES]

        # Buat DataFrame dari list of tuples
        input_row_tuple = tuple(feature_values_list)
        # Gunakan NUMERIC_FEATURES sebagai nama kolom
        input_df = spark.createDataFrame([input_row_tuple], NUMERIC_FEATURES)

        # Debugging
        print("\n--- Debugging PCA Input DataFrame ---")
        input_df.printSchema()
        input_df.show(truncate=False)
        print("--- End Debugging ---\n")

        # Gunakan model Pipeline untuk transformasi PCA
        transformed_df = model.transform(input_df)

        # Ambil hasil transformasi (kolom 'pcaFeatures' dari pipeline training)
        # Hasilnya adalah Vector, konversi ke list Python
        pca_features_vector = transformed_df.select("pcaFeatures").collect()[0][0]

        # Pastikan hasil adalah Vector sebelum konversi
        if isinstance(pca_features_vector, Vector):
             pca_features_list = pca_features_vector.toArray().tolist()
        else:
             # Tangani kasus jika output bukan Vector (seharusnya tidak terjadi)
             raise TypeError(f"Expected Vector output from PCA, but got {type(pca_features_vector)}")


        return jsonify({
            "model_used": model_name,
            "input_features": data,
            "transformed_pca_features": pca_features_list
        })

    except Exception as e:
        print(f"Error saat transformasi PCA: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan saat melakukan transformasi PCA: {e}"}), 500


# --- Endpoint 3: Frequent Itemsets (FP-Growth Results) ---
@app.route('/frequent_itemsets/<model_suffix>', methods=['GET']) # Menggunakan GET karena hanya mengambil hasil
def get_frequent_itemsets(model_suffix):
    results_name = f'fpgrowth_results_{model_suffix}' # Bentuk nama hasil lengkap
    if results_name not in loaded_models:
        return jsonify({"error": f"Hasil '{results_name}' tidak ditemukan"}), 404

    frequent_itemsets_df = loaded_models[results_name] # Ambil DataFrame hasil dari dictionary

    try:
        # Ambil semua baris dari DataFrame hasil FP-Growth
        # Konversi ke format list of dictionaries untuk JSON
        frequent_itemsets_list = [row.asDict() for row in frequent_itemsets_df.collect()]

        # FP-Growth menghasilkan kolom 'items' (Array[String]) dan 'freq' (Long)
        # Konversi array 'items' ke list Python
        for itemset in frequent_itemsets_list:
             if isinstance(itemset.get('items'), list): # Pastikan itu list (dari Array[String])
                  itemset['items'] = [str(item) for item in itemset['items']] # Konversi elemen ke string jika perlu
             # Konversi freq ke int
             if isinstance(itemset.get('freq'), int):
                  itemset['freq'] = int(itemset['freq'])


        return jsonify({
            "results_used": results_name,
            "frequent_itemsets": frequent_itemsets_list
        })

    except Exception as e:
        print(f"Error saat mengambil frequent itemsets: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan saat mengambil frequent itemsets: {e}"}), 500


if __name__ == '__main__':
    # use_reloader=False penting saat menggunakan SparkSession di Flask debug mode
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)