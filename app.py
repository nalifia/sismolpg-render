from flask import Flask, render_template, request, jsonify
import pandas as pd
import joblib
import os
import firebase_admin
from firebase_admin import credentials, db
import datetime
from flask_cors import CORS
import logging
import numpy as np
from sklearn.preprocessing import LabelEncoder
import threading
import time

# Konfigurasi Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Path absolut ke direktori aplikasi
app_dir = os.path.dirname(os.path.abspath(__file__))

def init_firebase():
    """Inisialisasi Firebase dengan error handling"""
    try:
        cred_path = "/etc/secrets/deteksikebocorangas-1917b-firebase-adminsdk-fbsvc-9f3b405891.json"
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://deteksikebocorangas-1917b-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
        logger.info("Firebase berhasil diinisialisasi")
    except Exception as e:
        logger.error(f"Gagal inisialisasi Firebase: {e}")
        raise

def load_model():
    """Memuat model machine learning dengan error handling"""
    try:
        model_path = os.path.join(app_dir, 'models', 'random_forest_model.pkl')
        if not os.path.exists(model_path):
            logger.error(f"File model tidak ditemukan di: {model_path}")
            return None
            
        model = joblib.load(model_path)
        logger.info(f"Model berhasil dimuat dari: {model_path}")
        logger.info(f"Tipe model: {type(model)}")
        if hasattr(model, 'classes_'):
            logger.info(f"Kelas model: {model.classes_}")
        return model
    except Exception as e:
        logger.error(f"Error saat memuat model: {e}", exc_info=True)
        return None

# Inisialisasi
init_firebase()
MODEL = load_model()
LABEL_ENCODER = LabelEncoder()

import os
from dotenv import load_dotenv
from telegram import Bot
import requests


load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = Bot(token=TOKEN)

def send_alert(message):
    bot = Bot(token=TOKEN)

send_alert('Halo gas detected!')

# === Kirim Notifikasi Telegram via HTTP Sinkron ===
def send_telegram_message(message):
    if not TOKEN or not CHAT_ID:
        print("Token atau Chat ID tidak ditemukan!")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print(f"✅ Pesan berhasil dikirim: {message}")
        else:
            print(f"❌ Gagal kirim pesan, status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Gagal kirim pesan: {e}")


ESP32_BUZZER_URL = "http://192.168.1.5/buzzer"  # Ganti <ESP32_IP> dengan IP ESP32 Anda

def send_buzzer_command(status):
    """Mengirimkan perintah untuk menyalakan buzzer di ESP32"""
    try:
        response = requests.post(ESP32_BUZZER_URL, json={'status': status})
        if response.status_code == 200:
            print(f"Buzzer status {status} berhasil dikirim ke ESP32.")
        else:
            print(f"Gagal mengirim status buzzer ke ESP32. Status code: {response.status_code}")
    except Exception as e:
        print(f"Gagal mengirim perintah ke ESP32: {e}")

# === Monitor Sensor ===
def monitor_gas():
    """Memantau data terbaru dan mengirimkan prediksi serta status ke Telegram"""
    while True:
        try:
            ref = db.reference('sensor_data')
            data = ref.get()

            if not data:
                print('No data found.')
                time.sleep(10)
                continue

            # Ambil data terbaru dari Firebase
            latest_timestamp = max(data.keys())
            latest_data = data[latest_timestamp]
            print(f"[Monitor] Latest Data: {latest_data}")

            # Ambil data untuk prediksi
            data_prediksi = {
                'MQ2_ADC': latest_data.get('MQ2_ADC', 0),
                'MQ2_PPM': latest_data.get('MQ2_PPM', 0),
                'MQ6_ADC': latest_data.get('MQ6_ADC', 0),
                'MQ6_PPM': latest_data.get('MQ6_PPM', 0),
                'Flame': latest_data.get('Flame', 0),
                'Suhu': latest_data.get('Suhu', 0),
                'Kelembapan': latest_data.get('Kelembapan', 0)
            }

            # Mengambil prediksi dari model
            prediksi = prediksi_kondisi(data_prediksi)
            kondisi = prediksi['kondisi']
            
            # Debugging: Cek hasil prediksi
            print(f"[Monitor] Hasil prediksi ML: {kondisi}")

            # Jika prediksi adalah "waspada" atau "bahaya", kirimkan ke Telegram
            if kondisi == 'bahaya':
                prediksi_message = "Bahaya ! Kebocoran gas tinggi atau api terdeteksi"
                send_telegram_message(prediksi_message)
                send_buzzer_command('bahaya')  # Mengirimkan perintah untuk menyalakan buzzer
            elif kondisi == 'waspada':
                prediksi_message = "Waspada! Ada potensi kebocoran gas"
                send_telegram_message(prediksi_message)
                send_buzzer_command('waspada')  # Mengirimkan perintah untuk menyalakan buzzer

        except Exception as e:
            print(f"[Monitor] Error: {e}")

        time.sleep(10)  # Delay untuk pengambilan data berikutnya



def prediksi_kondisi(data_baru):
    """Fungsi prediksi dengan error handling yang lebih baik"""
    logger.info(f"Menerima data baru untuk prediksi: {data_baru}")
    
    # Deklarasikan global MODEL di awal fungsi
    global MODEL
    
    if MODEL is None:
        logger.warning("Model tidak tersedia, mencoba memuat ulang...")
        MODEL = load_model()
        
        if MODEL is None:
            logger.error("Gagal memuat ulang model, mengembalikan prediksi default")
            return {
                'kondisi': 'aman',
                'probabilitas': {
                    'aman': 100.0,
                    'waspada': 0.0,
                    'bahaya': 0.0
                }
            }

    try:
        # Konversi data ke DataFrame dengan pengecekan tipe data
        features_dict = {
            'MQ2_ADC': float(data_baru.get('MQ2_ADC', 0)),
            'MQ2_PPM': float(data_baru.get('MQ2_PPM', 0)),
            'MQ6_ADC': float(data_baru.get('MQ6_ADC', 0)),
            'MQ6_PPM': float(data_baru.get('MQ6_PPM', 0)),
            'Flame': int(data_baru.get('Flame', 0)),
            'Suhu': float(data_baru.get('Suhu', 0)),
            'Kelembapan': float(data_baru.get('Kelembapan', 0))
        }
        
        logger.info(f"Features untuk model: {features_dict}")
        features = pd.DataFrame([features_dict])

        # Cek apakah fitur sesuai dengan yang diharapkan model
        logger.info(f"Kolom dataframe: {features.columns.tolist()}")
        
        # Prediksi
        logger.info("Melakukan prediksi dengan model...")
        prediksi = MODEL.predict(features)[0]
        logger.info(f"Hasil prediksi: {prediksi}")
        
        probabilitas = MODEL.predict_proba(features)[0]
        logger.info(f"Probabilitas prediksi: {probabilitas}")
        logger.info(f"Kelas model: {MODEL.classes_}")

        # Pemetaan prediksi ke label
        kondisi_map = {
            0: 'aman',
            2: 'waspada',
            1: 'bahaya'
        }

        # Mapping probabilitas
        hasil_probabilitas = {}
        for i, label in enumerate(MODEL.classes_):
            hasil_probabilitas[int(label)] = round(probabilitas[i] * 100, 2)
        
        logger.info(f"Hasil probabilitas diformat: {hasil_probabilitas}")

        hasil_prediksi = {
            'kondisi': kondisi_map.get(prediksi, 'AMAN'),
            'probabilitas': hasil_probabilitas
        }
        
        logger.info(f"Hasil akhir prediksi: {hasil_prediksi}")
        return hasil_prediksi

    except Exception as e:
        logger.error(f"Error saat prediksi: {e}", exc_info=True)
        return {
            'kondisi': 'aman',
            'probabilitas': {
                'aman': 100.0,
                'waspada': 0.0,
                'bahaya': 0.0
            }
        }


@app.route('/api/data/latest')
def get_latest_data():
    try:
        ref = db.reference('sensor_data')
        data = ref.get()
        
        if not data:
            return jsonify({"error": "Tidak ada data sensor"}), 404

        # Cari data terbaru
        latest_timestamp = max(data.keys())
        latest_data = data[latest_timestamp]
        
        # Log data untuk debugging
        logger.info(f"Data terbaru dari Firebase: {latest_data}")

        # Struktur data untuk prediksi
        data_prediksi = {
            'MQ2_ADC': latest_data.get('MQ2_ADC', 0),
            'MQ2_PPM': latest_data.get('MQ2_PPM', 0),
            'MQ6_ADC': latest_data.get('MQ6_ADC', 0),
            'MQ6_PPM': latest_data.get('MQ6_PPM', 0),
            'Flame': latest_data.get('Flame', 0),
            'Suhu': latest_data.get('Suhu', 0),
            'Kelembapan': latest_data.get('Kelembapan', 0)
        }
        
        # Log data prediksi
        logger.info(f"Data untuk prediksi ML: {data_prediksi}")

        # Prediksi kondisi
        prediksi = prediksi_kondisi(data_prediksi)
        logger.info(f"Hasil prediksi ML: {prediksi}")

        # Gabungkan data
        response_data = {
            **latest_data,
            'timestamp': latest_timestamp,
            'prediksi_ml': prediksi
        }
        
        # Log response data
        logger.info(f"Data response final: {response_data}")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Gagal mengambil data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def komparasi_klasifikasi(data_firebase):
    """Membandingkan klasifikasi alat vs prediksi ML"""
    try:
        # Persiapkan data untuk prediksi
        data_prediksi = {
            'MQ2_ADC': data_firebase.get('MQ2_ADC', 0),
            'MQ2_PPM': data_firebase.get('MQ2_PPM', 0),
            'MQ6_ADC': data_firebase.get('MQ6_ADC', 0),
            'MQ6_PPM': data_firebase.get('MQ6_PPM', 0),
            'Flame': data_firebase.get('Flame', 0),
            'Suhu': data_firebase.get('Suhu', 0),
            'Kelembapan': data_firebase.get('Kelembapan', 0)
        }

        # Prediksi ML
        prediksi_ml = prediksi_kondisi(data_prediksi)
        klasifikasi_alat = data_firebase.get('Klasifikasi', '').lower() or data_firebase.get('klasifikasi', 'AMAN').lower()

        # Komparasi
        return {
            'klasifikasi_alat': klasifikasi_alat,
            'prediksi_ml': prediksi_ml['kondisi'],
            'probabilitas_ml': prediksi_ml['probabilitas'],
            'akurasi': klasifikasi_alat == prediksi_ml['kondisi']
        }

    except Exception as e:
        logger.error(f"Gagal komparasi klasifikasi: {e}")
        return None

@app.route('/api/komparasi_klasifikasi')
def api_komparasi_klasifikasi():
    """Endpoint untuk membandingkan klasifikasi"""
    try:
        ref = db.reference('sensor_data')
        data = ref.get()
        
        if not data:
            return jsonify({"error": "Tidak ada data sensor"}), 404

        # Ambil data terbaru
        latest_timestamp = max(data.keys())
        latest_data = data[latest_timestamp]

        # Lakukan komparasi
        hasil_komparasi = komparasi_klasifikasi(latest_data)
        
        return jsonify(hasil_komparasi)

    except Exception as e:
        logger.error(f"Gagal pada API komparasi: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_model')
def check_model():
    """Endpoint untuk memeriksa status model ML"""
    try:
        if MODEL is None:
            return jsonify({
                "status": "error", 
                "message": "Model tidak dimuat"
            }), 500
            
        # Buat data uji
        test_data = {
            'MQ2_ADC': 150,
            'MQ2_PPM': 0.75,
            'MQ6_ADC': 250,
            'MQ6_PPM': 1.2,
            'Flame': 0,
            'Suhu': 28.5,
            'Kelembapan': 70.0
        }
        
        # Coba prediksi
        hasil = prediksi_kondisi(test_data)
        
        return jsonify({
            "status": "success",
            "message": "Model berfungsi",
            "model_info": {
                "type": str(type(MODEL)),
                "classes": MODEL.classes_.tolist() if hasattr(MODEL, 'classes_') else None
            },
            "test_prediction": hasil
        })
    except Exception as e:
        logger.error(f"Gagal memeriksa model: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Gagal memeriksa model: {str(e)}"
        }), 500

@app.route('/api/check_model_path')
def check_model_path():
    """Endpoint untuk memeriksa keberadaan file model"""
    model_dir = os.path.join(app_dir, 'models')
    files = os.listdir(model_dir) if os.path.exists(model_dir) else []
    return jsonify({
        "app_dir": app_dir,
        "model_dir": model_dir,
        "model_dir_exists": os.path.exists(model_dir),
        "files": files
    })

@app.route('/api/get_history')

def get_history():
    try:
        ref = db.reference('sensor_data')
        data = ref.get()
        
        if not data:
            return jsonify([])

        history_list = []
        for timestamp, entry in data.items():
            try:
                bulan_mapping = {
                    'Januari': '01',
                    'Februari': '02',
                    'Maret': '03',
                    'April': '04',
                    'Mei': '05',
                    'Juni': '06',
                    'Juli': '07',
                    'Agustus': '08',
                    'September': '09',
                    'Oktober': '10',
                    'November': '11',
                    'Desember': '12'
                }

                parts = timestamp.split()
                if len(parts) == 4:
                    day, month_str, year, time_part = parts
                    month = bulan_mapping.get(month_str, '01')
                    iso_timestamp = f"{year}-{month}-{day.zfill(2)}T{time_part}"
                else:
                    iso_timestamp = timestamp
                
            except Exception as e:
                iso_timestamp = timestamp
            
            entry['timestamp'] = iso_timestamp
            history_list.append(entry)

        history_list.sort(key=lambda x: x['timestamp'], reverse=True)
        history_list = history_list[:50]
        
        return jsonify(history_list)
    
    except Exception as e:
        logger.error(f"Gagal mengambil history: {e}")
        return jsonify({"error": str(e)}), 500
    
# Route untuk halaman web
@app.route('/')
def home():
    return render_template('dashboard.html', active_page='dashboard', body_class='dashboard_page')

from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d %B %Y %H:%M:%S'):
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime(format)
    except Exception as e:
        return value    

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', active_page='dashboard', body_class='dashboard_page')

@app.route('/history')
def history():
    try:
        ref = db.reference('sensor_data')
        data = ref.get()
        
        if not data:
            return render_template('history.html', logs=[])

        history_list = []
        bulan_mapping = {
            'Januari': '01', 'Februari': '02', 'Maret': '03',
            'April': '04', 'Mei': '05', 'Juni': '06',
            'Juli': '07', 'Agustus': '08', 'September': '09',
            'Oktober': '10', 'November': '11', 'Desember': '12'
        }

        for timestamp, entry in data.items():
            try:
                parts = timestamp.split()
                if len(parts) == 4:  # 11 Mei 2025 09:45:22
                    day, month_str, year, time_part = parts
                    month = bulan_mapping.get(month_str, '01')
                    iso_timestamp = f"{year}-{month}-{day.zfill(2)}T{time_part}"
                else:
                    iso_timestamp = timestamp
            except Exception:
                iso_timestamp = timestamp

            entry['timestamp'] = iso_timestamp
            history_list.append(entry)

        history_list.sort(key=lambda x: x['timestamp'], reverse=True)
        history_list = history_list[:50]
        
        return render_template('history.html', logs=history_list, active_page='history', body_class='history_page')
    
    except Exception as e:
        logger.error(f"Gagal mengambil history: {e}")
        return render_template('history.html', logs=[])


@app.route('/grafik')
def grafik():
    return render_template('grafik.html', active_page='grafik', body_class='grafik_page')

@app.route('/about')
def about():
    return render_template('about.html', active_page='about', body_class='about_page')

@app.route('/api/inject_test_data')
def inject_test_data():
    """Endpoint untuk menyuntikkan data uji ke Firebase"""
    try:
        ref = db.reference('sensor_data')
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        test_data = {
            timestamp: {
                'MQ2_ADC': 150,
                'MQ2_PPM': 0.75,
                'MQ6_ADC': 250,
                'MQ6_PPM': 1.2,
                'Flame': 0,
                'Suhu': 28.5,
                'Kelembapan': 70.0,
                'Klasifikasi': 'AMAN'
            }
        }
        
        ref.update(test_data)
        
        return jsonify({
            "status": "success",
            "message": "Data uji berhasil ditambahkan",
            "data": test_data
        })
    except Exception as e:
        logger.error(f"Gagal menambahkan data uji: {e}")
        return jsonify({
            "status": "error",
            "message": f"Gagal menambahkan data uji: {str(e)}"
        }), 500


threading.Thread(target=monitor_gas, daemon=True).start()