"""
Módulo de Autenticação - PostgreSQL Only
"""

from flask_login import LoginManager, UserMixin, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
from flask import redirect, url_for, flash
import os

# Inicializar extensões
login_manager = LoginManager()
bcrypt = Bcrypt()

class User(UserMixin):
    def __init__(self, id, username, password, role, empresa_id=None, is_demo=False):
        self.id = id
        self.username = username
        self.password = password
        self.role = role or 'OPERADOR'  # Default para OPERADOR
        self.empresa_id = empresa_id
        self.is_demo = is_demo  # Flag para usuários de demonstração
    
    @property
    def is_super_admin(self):
        """Verifica se é o super administrador do sistema (dono do SaaS)"""
        return self.username == 'admin'
    
    @property
    def is_empresa_admin(self):
        """Verifica se é administrador da empresa (cliente do SaaS)"""
        return self.role in ['Admin', 'ADMIN'] and not self.is_super_admin

@login_manager.user_loader
def load_user(user_id):
    """Carregar usuário do banco de dados PostgreSQL"""
    from config import Config
    import psycopg2
    
    try:
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash, role, empresa_id, COALESCE(is_demo, false) FROM usuarios WHERE id = %s', (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            return User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], bool(user_data[5]))
        return None
    except Exception as e:
        print(f"Erro ao carregar usuário: {e}")
        return None

def authenticate_user(username, password):
    """Autenticar usuário via PostgreSQL"""
    from config import Config
    import psycopg2
    
    try:
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash, role, empresa_id, COALESCE(is_demo, false) FROM usuarios WHERE username = %s AND ativo = true', (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user_data:
            return None, 'Usuário não encontrado ou inativo'
        
        if not bcrypt.check_password_hash(user_data[2], password):
            return None, 'Senha incorreta'
        
        user = User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], bool(user_data[5]))
        return user, None
        
    except Exception as e:
        return None, f'Erro ao autenticar: {str(e)}'

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

def log_action(user_id=None, action=None, table=None, record_id=None, details='', ip=None):
    """Registrar ação do usuário via PostgreSQL
    
    Aceita múltiplas formas de chamada:
    - log_action(user_id, action, details)
    - log_action(user_id, action, table, record_id, details, ip)
    - log_action('mensagem simples')
    """
    from config import Config
    import psycopg2
    
    # Normalizar argumentos para diferentes formas de chamada
    # Caso: log_action('mensagem simples') - apenas 1 arg string
    if user_id is not None and action is None:
        details = str(user_id)
        user_id = None
    # Caso: log_action(user_id, action, 'detalhes') - 3 args sem table/record_id
    elif table is not None and record_id is None and not details:
        details = str(table)
        table = None
    
    # Compor detalhes completos
    full_details = details or ''
    if table:
        full_details = f"[{table}:{record_id}] {full_details}"
    if ip:
        full_details = f"{full_details} (IP: {ip})"
    
    try:
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs_acoes (usuario_id, acao, detalhes)
            VALUES (%s, %s, %s)
        ''', (user_id, action or 'SYSTEM', full_details))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao registrar log: {e}")
