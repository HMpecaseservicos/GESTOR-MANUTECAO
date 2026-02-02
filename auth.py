"""
Módulo de Autenticação
"""

from flask_login import LoginManager, UserMixin, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
from flask import redirect, url_for, flash
import sqlite3

# Inicializar extensões
login_manager = LoginManager()
bcrypt = Bcrypt()

class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    """Carregar usuário do banco de dados"""
    conn = sqlite3.connect('database/frota.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password_hash, role FROM usuarios WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

def init_auth_tables(conn):
    """Inicializar tabelas de autenticação"""
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            ativo BOOLEAN DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_login TIMESTAMP
        )
    ''')
    
    # Tabela de logs de ações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_acoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            acao TEXT,
            detalhes TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    conn.commit()

def authenticate_user(username, password):
    """Autenticar usuário"""
    conn = sqlite3.connect('database/frota.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password_hash, role FROM usuarios WHERE username = ?', (username,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data and bcrypt.check_password_hash(user_data[2], password):
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

def admin_required(f):
    """Decorator para rotas que requerem admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acesso negado. Requer permissões de administrador.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def tecnico_required(f):
    """Decorator para rotas que requerem técnico ou admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'tecnico']:
            flash('Acesso negado. Requer permissões de técnico.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_action(user_id, action, details=''):
    """Registrar ação do usuário"""
    try:
        conn = sqlite3.connect('database/frota.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs_acoes (usuario_id, acao, detalhes)
            VALUES (?, ?, ?)
        ''', (user_id, action, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao registrar log: {e}")
