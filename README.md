# 📚 MPedia Math AI Assistant

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-brightgreen)
![Flask](https://img.shields.io/badge/flask-2.0%2B-lightgrey)
![License](https://img.shields.io/badge/license-MIT-orange)

## 🎯 Tentang MPedia Math AI Assistant

MPedia Math AI Assistant adalah platform pembelajaran matematika berbasis AI yang dirancang untuk membantu siswa belajar matematika dengan cara yang interaktif dan menyenangkan. Platform ini dapat diakses melalui website dan WhatsApp, menjadikannya solusi pembelajaran yang fleksibel dan mudah diakses.

### ✨ Fitur Utama

#### 🌐 Akses Multi-Platform
- **Website Interface**: Antarmuka web yang modern dan responsif
- **WhatsApp Integration**: Akses melalui chat WhatsApp untuk pembelajaran mobile
- **Cross-Platform Sync**: History pembelajaran tersimpan di kedua platform

#### 🤖 AI Teaching Assistant
- Penjelasan step-by-step yang mudah dipahami
- Pendekatan pembelajaran yang adaptif
- Contoh soal yang relevan
- Fokus pada pemahaman konsep

#### 🛠 Fitur Teknis
- Real-time chat processing
- Sistem manajemen sesi
- Database terintegrasi
- Health monitoring system
- Support untuk gambar matematika

### 🚀 Cara Menggunakan

#### Via Website
1. Kunjungi [website-url]
2. Mulai chat dengan AI Math Assistant
3. Ajukan pertanyaan matematika Anda

#### Via WhatsApp
1. Simpan nomor bot: [nomor-whatsapp]
2. Kirim pesan "/mulai" untuk memulai sesi
3. Ajukan pertanyaan matematika Anda

### 📌 Perintah WhatsApp
- `/mulai` - Memulai sesi belajar
- `/status` - Cek status sesi
- `/clear` - Hapus history chat
- `/berhenti` - Mengakhiri sesi

### 🛠 Teknologi yang Digunakan
- Python & Flask
- Ollama LLM
- SQLite Database
- WhatsApp API MPedia
- TailwindCSS
- JavaScript

### 📋 Persyaratan Sistem
- Python 3.8+
- Flask 2.0+
- SQLite3

### 🔧 Instalasi

```bash
# Clone repository
git clone https://github.com/classyid/mpedia-math-tutor.git

# Install dependencies
pip install flask langchain-ollama

# Setup database
python init_db.py

# Jalankan aplikasi
python app.py
