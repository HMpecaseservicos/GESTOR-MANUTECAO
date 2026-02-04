"""
Helpers para Sistema Multi-Empresa
Funções auxiliares para filtrar dados por empresa
"""

from flask_login import current_user
from functools import wraps
from flask import abort

def get_empresa_id():
    """Retorna o ID da empresa do usuário logado"""
    if not current_user.is_authenticated:
        return None
    return getattr(current_user, 'empresa_id', 1)  # Default para empresa 1

def filtro_empresa(query):
    """Adiciona filtro de empresa_id na query SQL"""
    empresa_id = get_empresa_id()
    if 'WHERE' in query.upper():
        return query.replace('WHERE', f'WHERE empresa_id = {empresa_id} AND')
    else:
        # Adicionar WHERE antes de ORDER BY, GROUP BY ou LIMIT
        for keyword in ['ORDER BY', 'GROUP BY', 'LIMIT']:
            if keyword in query.upper():
                return query.replace(keyword, f'WHERE empresa_id = {empresa_id} {keyword}')
        # Se não tiver nenhum, adicionar no final
        return f"{query} WHERE empresa_id = {empresa_id}"

def empresa_required(f):
    """Decorator que garante que apenas usuários da mesma empresa acessem os dados"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not hasattr(current_user, 'empresa_id') or not current_user.empresa_id:
            abort(403, description="Usuário não associado a nenhuma empresa")
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator para funções que só o super admin pode acessar"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.username != 'admin':  # Super admin
            abort(403, description="Acesso restrito ao administrador do sistema")
        return f(*args, **kwargs)
    return decorated_function
