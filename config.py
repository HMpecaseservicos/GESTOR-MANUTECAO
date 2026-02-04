"""
Arquivo de configuração do Sistema de Gestão de Manutenção de Frota
================================================================

Este arquivo centraliza todas as configurações do sistema para
facilitar manutenção e customização.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class Config:
    """Configuração base do sistema"""
    
    # Configurações básicas
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    
    # Configurações do banco de dados
    # Prioridade: DATABASE_URL (produção PostgreSQL) > SQLite local (desenvolvimento)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        # Desenvolvimento local com SQLite
        DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'frota.db')
        DATABASE_URL = f'sqlite:///{DATABASE_PATH}'
    else:
        # Produção com PostgreSQL (Fly.io)
        # Fix para Heroku/Fly.io que usam postgres:// em vez de postgresql://
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        DATABASE_PATH = None  # Não usado em produção
    
    # Detectar se está usando PostgreSQL
    IS_POSTGRES = DATABASE_URL.startswith('postgresql://')
    
    # Configurações da aplicação
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # Configurações de sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações de segurança
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Token não expira
    
    # Rate Limiting
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    
    # Configurações de upload (para futura implementação)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # Configurações de relatórios
    REPORTS_FOLDER = os.path.join(os.path.dirname(__file__), 'reports')
    
    # Configurações de logs
    LOG_FOLDER = os.path.join(os.path.dirname(__file__), 'logs')
    LOG_FILE = os.path.join(LOG_FOLDER, 'app.log')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    @staticmethod
    def ensure_directories():
        """Garante que os diretórios necessários existem"""
        directories = [
            Config.UPLOAD_FOLDER,
            Config.REPORTS_FOLDER,
            Config.LOG_FOLDER,
            os.path.join(Config.UPLOAD_FOLDER, 'temp'),
            os.path.join(Config.REPORTS_FOLDER, 'temp')
        ]
        
        # Adicionar DATABASE_PATH apenas se estiver em desenvolvimento (SQLite)
        if Config.DATABASE_PATH:
            directories.insert(0, os.path.dirname(Config.DATABASE_PATH))
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False

# Configuração baseada em ambiente
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}