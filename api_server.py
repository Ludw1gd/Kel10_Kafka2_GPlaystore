from flask import Flask, request, jsonify
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel # Model yang disimpan adalah PipelineModel
from pyspark.ml.linalg import Vectors # Untuk membuat Vector dari input
from pyspark.sql.types import StructType, StructField, DoubleType
from pyspark.sql import Row # Import Row
import os
import sys # Untuk menambahkan PySpark ke PATH jika perlu
import traceback # Import traceback

spark = SparkSession.builder \
    .appName("PlaystoreKMeansAPI") \
    .config("spark.driver.memory", "8g") \
    .master("local[*]") \
    .getOrCreate()
    
print("Spark Session berhasil diinisialisasi di API.")

app = Flask(__name__)

# Lokasi model yang disimpan oleh Spark script
MODEL_BASE_PATH = "/app/trained_models"


# Dictionary untuk menyimpan model yang dimuat
loaded_models = {}

# Nama kolom fitur yang digunakan saat training (harus sama!)
# Urutan ini PENTING karena akan digunakan untuk membuat Vector
FEATURE_COLS = ['Rating', 'Reviews', 'Size', 'Installs', 'Price']

def load_models():
    """Memuat semua model saat API startup."""
    print(f"Mencari model di: {MODEL_BASE_PATH}")
    if not os.path.exists(MODEL_BASE_PATH):
        print(f"Direktori model tidak ditemukan: {MODEL_BASE_PATH}")
        return
    
    model_dirs = [d for d in os.listdir(MODEL_BASE_PATH) if os.path.isdir(os.path.join(MODEL_BASE_PATH, d))]
    if not model_dirs:
        print("Tidak ada sub-direktori model ditemukan di MODEL_BASE_PATH.")
    
    for model_name in model_dirs:
        model_path = os.path.join(MODEL_BASE_PATH, model_name)
        try:
            model = PipelineModel.load(model_path)
            loaded_models[model_name] = model
            print(f"Model '{model_name}' berhasil dimuat dari {model_path}")
        except Exception as e:
            print(f"Gagal memuat model '{model_name}' dari {model_path}: {e}")
            traceback.print_exc()

with app.app_context():
    load_models()
        
    # for model_name in model_dirs:
    #     model_path = os.path.join(MODEL_BASE_PATH, model_name)
    #     try:
    #         # Muat model Spark Pipeline
    #         # Pastikan SparkSession sudah aktif saat memuat model
    #         model = PipelineModel.load(model_path)
    #         loaded_models[model_name] = model
    #         print(f"Model '{model_name}' berhasil dimuat dari {model_path}")
    #     except Exception as e:
    #         print(f"Gagal memuat model '{model_name}' dari {model_path}: {e}")
    #         # Jika gagal memuat, mungkin ada masalah dengan file model atau versi Spark/PySpark

# Muat model saat aplikasi Flask dimulai
# Menggunakan app.app_context() memastikan SparkSession sudah aktif
# with app.app_context():
#     load_models()

# Endpoint untuk prediksi clustering
@app.route('/cluster/<model_name>', methods=['POST'])
def cluster_predict(model_name):
    if model_name not in loaded_models:
        return jsonify({"error": f"Model '{model_name}' tidak ditemukan"}), 404

    model = loaded_models[model_name]
    data = request.json

    if not data or not all(col in data for col in FEATURE_COLS):
        return jsonify({"error": f"Input JSON harus mengandung semua fitur: {FEATURE_COLS}"}), 400
    
    try:
        # Ambil nilai fitur dari input JSON dalam urutan yang benar
        # Asumsikan nilai di JSON sudah bersih dan numerik (float/int)
        feature_values_dict = {col: data[col] for col in FEATURE_COLS}
        
        # Buat DataFrame dengan kolom-kolom fitur asli, bukan hanya kolom 'features'
        # Skema DataFrame harus sesuai dengan input VectorAssembler
        
        # Definisikan skema input sesuai FEATURE_COLS
        input_schema = StructType([StructField(col_name, DoubleType(), False) for col_name in FEATURE_COLS])
        
        # Buat DataFrame dari dictionary nilai fitur
        # Perlu membuat list of Row
        input_row = [feature_values_dict]
        input_df = spark.createDataFrame(input_row, input_schema)
        
        # --- DEBUGGING: Periksa DataFrame Input ---
        print("\n--- Debugging Input DataFrame ---")
        print("Input DataFrame Schema:")
        input_df.printSchema()
        print("\nInput DataFrame Data:")
        input_df.show(truncate=False)
        print("\nInput DataFrame Columns:")
        print(input_df.columns)
        print("--- End Debugging ---\n")
        # --- AKHIR DEBUGGING ---
        
        # Gunakan model Pipeline untuk prediksi cluster
        prediction_df = model.transform(input_df)
        
        # Ambil hasil prediksi (cluster ID)
        # Nama kolom prediksi default dari KMeans adalah 'prediction'
        cluster_id = prediction_df.collect()[0].prediction
        
        return jsonify({
            "model_used": model_name,
            "input_features": data,
            "predicted_cluster_id": int(cluster_id)
        })
    
    except Exception as e:
        print(f"Error saat prediksi: {e}")
        traceback.print_exc() # Cetak traceback lengkap saat prediksi
        return jsonify({"error": f"Terjadi kesalahan saat melakukan prediksi: {e}"}), 500

if __name__ == '__main__':
    # Jalankan API
    # host='0.0.0.0' agar bisa diakses dari luar localhost jika perlu
    # debug=True hanya untuk pengembangan
    # use_reloader=False penting jika menggunakan SparkSession,
    # karena reloader bisa membuat SparkSession terduplikasi
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)