# app.py
from flask import Flask, render_template, request, jsonify, session
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging
from datetime import datetime
import sqlite3
import uuid
import json
import base64
import os

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400

# Konfigurasi Model
OLLAMA_CONFIG = {
    "model": "qwen",
    "base_url": "http://<ip-serverOllama>:11434",
    "temperature": 0.7,
    "top_k": 40,
    "top_p": 0.95,
    "num_ctx": 2048,
    "repeat_penalty": 1.1
}

def init_db():
    """Drop dan recreate tables untuk menghindari masalah struktur"""
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    
    # Drop tables if exist
    c.execute('DROP TABLE IF EXISTS messages')
    c.execute('DROP TABLE IF EXISTS sessions')
    c.execute('DROP TABLE IF EXISTS whatsapp_users')
    
    # Create tables with new structure
    c.execute('''CREATE TABLE sessions
                 (session_id TEXT PRIMARY KEY, 
                  created_at TIMESTAMP)''')
                  
    c.execute('''CREATE TABLE messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  role TEXT,
                  content TEXT,
                  timestamp TIMESTAMP,
                  source TEXT DEFAULT 'web',
                  FOREIGN KEY (session_id) REFERENCES sessions(session_id))''')

    # Tambah tabel untuk status pengguna WhatsApp
    c.execute('''CREATE TABLE whatsapp_users
                 (phone_number TEXT PRIMARY KEY,
                  status TEXT DEFAULT 'inactive',
                  name TEXT,
                  last_updated TIMESTAMP)''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# Initialize database
init_db()

# Initialize LLM
try:
    llm = ChatOllama(**OLLAMA_CONFIG)
    logger.info("LLM initialized successfully")
except Exception as e:
    logger.error(f"Error initializing LLM: {str(e)}")
    llm = None

def get_system_prompt() -> SystemMessage:
    return SystemMessage(content="""Kamu adalah asisten guru matematika yang sabar dan membantu.
Panduan mengajar:
1. Jelaskan konsep dengan sederhana dan mudah dipahami
2. Berikan langkah penyelesaian step by step
3. Sertakan contoh yang relevan
4. Jika siswa bingung, coba pendekatan penjelasan yang berbeda
5. Dorong siswa untuk berpikir kritis
Berikan jawaban dalam bahasa Indonesia yang jelas, singkat dan edukatif dengan contoh soal jika diperlukan.""")

def save_message(session_id, role, content, source="web"):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('INSERT INTO messages (session_id, role, content, timestamp, source) VALUES (?, ?, ?, ?, ?)',
              (session_id, role, content, datetime.now(), source))
    conn.commit()
    conn.close()

def get_chat_history(session_id):
    """Get chat history with better memory management"""
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    
    # Ambil maksimal 10 percakapan terakhir untuk konteks
    c.execute('''
        SELECT role, content 
        FROM messages 
        WHERE session_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''', (session_id,))
    
    # Balik urutan agar yang lama tampil duluan
    messages = [{"role": role, "content": content} 
               for role, content in reversed(c.fetchall())]
    
    conn.close()
    return messages

def get_all_chat_history(session_id):
    """Get complete chat history for display"""
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''
        SELECT role, content, timestamp 
        FROM messages 
        WHERE session_id = ? 
        ORDER BY timestamp
    ''', (session_id,))
    
    messages = [{
        "role": role,
        "content": content,
        "timestamp": timestamp
    } for role, content, timestamp in c.fetchall()]
    
    conn.close()
    return messages

def clear_chat_history(session_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()

def get_user_status(phone_number):
    try:
        conn = sqlite3.connect('chat_history.db')
        c = conn.cursor()
        c.execute('SELECT status FROM whatsapp_users WHERE phone_number = ?', (phone_number,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return 'inactive'
    except Exception as e:
        logger.error(f"Error getting user status: {str(e)}")
        return 'inactive'

def set_user_status(phone_number, status, name=''):
    try:
        conn = sqlite3.connect('chat_history.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO whatsapp_users 
                     (phone_number, status, name, last_updated)
                     VALUES (?, ?, ?, ?)''', 
                     (phone_number, status, name, datetime.now()))
        conn.commit()
        conn.close()
        logger.info(f"User {phone_number} status set to {status}")
        return True
    except Exception as e:
        logger.error(f"Error setting user status: {str(e)}")
        return False

def prepare_llm_messages(chat_history):
    """Prepare messages for LLM with system prompt"""
    return [
        get_system_prompt(),
        *[HumanMessage(content=msg["content"]) if msg["role"] == "user" 
          else AIMessage(content=msg["content"]) 
          for msg in chat_history]
    ]

# Web Routes
@app.route('/')
def home():
    if 'session_id' not in session:
        session.permanent = True
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        conn = sqlite3.connect('chat_history.db')
        c = conn.cursor()
        c.execute('INSERT INTO sessions (session_id, created_at) VALUES (?, ?)',
                  (session_id, datetime.now()))
        conn.commit()
        conn.close()
    
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    if llm is None:
        return jsonify({'error': 'LLM not initialized properly'}), 500
    
    try:
        data = request.json
        user_input = data['message']
        session_id = session.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Invalid session'}), 400
        
        if user_input.lower() == 'clear':
            clear_chat_history(session_id)
            return jsonify({
                'response': 'Chat history cleared',
                'chat_log': []
            })
        
        # Save user message
        save_message(session_id, "user", user_input)
        
        # Get recent chat history for context
        chat_history = get_chat_history(session_id)
        
        # Prepare messages for LLM
        llm_messages = prepare_llm_messages(chat_history)
        
        # Generate response
        response = llm.invoke(llm_messages)
        
        # Save AI response
        save_message(session_id, "assistant", response.content)
        
        # Get complete chat history for display
        full_history = get_all_chat_history(session_id)
        
        return jsonify({
            'response': response.content,
            'chat_log': full_history
        })
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history_route():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify([])
    return jsonify(get_all_chat_history(session_id))

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'llm_status': 'initialized' if llm else 'not initialized',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# WhatsApp Webhook endpoint
@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        return jsonify({
            "status": "active",
            "message": "WhatsApp webhook is running. Send POST request to interact."
        })

    try:
        data = request.json
        if not data:
            return '', 204

        with open('whatsapp.txt', 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now()}]\n{json.dumps(data, ensure_ascii=False)}\n\n')

        device = data.get('device', '')
        message = data.get('message', '').strip()
        from_user = data.get('from', '')
        name = data.get('name', '')
        buffer_image = data.get('bufferImage')

        # Check keywords
        if message.lower() == '/mulai':
            set_user_status(from_user, 'active', name)
            # Create new session if doesn't exist
            session_id = f"wa_{from_user}"
            save_message(session_id, "system", "Sesi baru dimulai")
            return jsonify({
                "text": "Selamat datang di Asisten Guru Matematika AI! 🎓\n\n"
                        "Saya siap membantu Anda belajar matematika. Silakan ajukan pertanyaan Anda.\n\n"
                        "Perintah yang tersedia:\n"
                        "- /status : Cek status sesi Anda\n"
                        "- /clear : Hapus history chat\n"
                        "- /berhenti : Mengakhiri sesi belajar"
            })
        
        elif message.lower() == '/berhenti':
            set_user_status(from_user, 'inactive', name)
            session_id = f"wa_{from_user}"
            save_message(session_id, "system", "Sesi diakhiri")
            return jsonify({
                "text": "Terima kasih telah menggunakan Asisten Guru Matematika AI! 👋\n\n"
                        "Ketik /mulai jika Anda ingin belajar lagi."
            })
        
        elif message.lower() == '/status':
            user_status = get_user_status(from_user)
            status_text = "aktif" if user_status == 'active' else "tidak aktif"
            return jsonify({
                "text": f"Status sesi Anda saat ini: {status_text}\n\n"
                        f"{'Anda bisa langsung bertanya' if user_status == 'active' else 'Ketik /mulai untuk memulai sesi belajar'}"
            })
        
        elif message.lower() == '/clear':
            session_id = f"wa_{from_user}"
            user_status = get_user_status(from_user)
            
            if user_status != 'active':
                return jsonify({
                    "text": "Anda harus memulai sesi terlebih dahulu dengan mengetik /mulai"
                })
            
            clear_chat_history(session_id)
            save_message(session_id, "system", "History chat dibersihkan")
            return jsonify({
                "text": "History chat telah dibersihkan.\nAnda bisa mulai bertanya lagi!"
            })

        user_status = get_user_status(from_user)
        if user_status != 'active':
            return '', 204

        if buffer_image:
            try:
                image_data = base64.b64decode(buffer_image)
                os.makedirs('images', exist_ok=True)
                filename = f'images/{from_user}_{int(datetime.now().timestamp())}.png'
                with open(filename, 'wb') as f:
                    f.write(image_data)
                logger.info(f"Saved image: {filename}")
            except Exception as e:
                logger.error(f"Error saving image: {str(e)}")

        if message and user_status == 'active':
            session_id = f"wa_{from_user}"
            
            # Save user message
            save_message(session_id, "user", message)
            
            # Get recent chat history for context
            chat_history = get_chat_history(session_id)
            
            try:
                # Prepare messages with context
                llm_messages = prepare_llm_messages(chat_history)
                
                # Get AI response
                response = llm.invoke(llm_messages)
                ai_response = response.content
                
                # Save AI response
                save_message(session_id, "assistant", ai_response)
                
                return jsonify({"text": ai_response})
                
            except Exception as e:
                logger.error(f"Error getting AI response: {str(e)}")
                return jsonify({
                    "text": "Maaf, terjadi kesalahan dalam memproses pesan Anda."
                    "\nSilakan coba lagi atau ketik /clear jika mengalami masalah."
                })

        return '', 204

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return jsonify({"text": "Terjadi kesalahan sistem"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
