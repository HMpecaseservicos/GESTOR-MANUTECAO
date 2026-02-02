import sys
import os

# ====================================
# WSGI Configuration for PythonAnywhere
# ====================================

# 🔧 ALTERE AQUI: Substitua 'seuusuario' pelo seu username do PythonAnywhere
project_home = '/home/seuusuario/gestor_frota'

# Adicionar o diretório do projeto ao Python path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Configurar ambiente de produção
os.environ['FLASK_ENV'] = 'production'
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

# Importar a aplicação Flask
from app import app as application

# Configurações adicionais para PythonAnywhere
application.config.update(
    SESSION_COOKIE_SECURE=True,  # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)
