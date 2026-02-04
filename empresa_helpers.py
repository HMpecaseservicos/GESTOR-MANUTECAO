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


# =============================================
# HELPERS DE TIPO DE OPERAÇÃO (ETAPA 1 HÍBRIDO)
# =============================================

def get_tipo_operacao():
    """
    Retorna o tipo de operação da empresa do usuário logado.
    Valores possíveis: 'FROTA' ou 'SERVICO'
    Default: 'FROTA' (comportamento original)
    """
    from flask import g
    if hasattr(g, 'empresa') and g.empresa:
        return g.empresa.get('tipo_operacao', 'FROTA')
    return 'FROTA'


def is_frota():
    """
    Verifica se a empresa logada opera no modo FROTA.
    Retorna True se for FROTA ou se não houver empresa (fallback seguro).
    """
    return get_tipo_operacao() == 'FROTA'


def is_servico():
    """
    Verifica se a empresa logada opera no modo SERVIÇO.
    Retorna True apenas se explicitamente configurado como SERVICO.
    """
    return get_tipo_operacao() == 'SERVICO'


def servico_required(f):
    """
    Decorator que bloqueia acesso a rotas exclusivas do modo SERVICO.
    Empresas FROTA recebem 403 Forbidden.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not is_servico():
            abort(403, description="Este recurso está disponível apenas para empresas de Prestação de Serviços")
        return f(*args, **kwargs)
    return decorated_function


# =============================================
# HELPERS DE RBAC (ETAPA 10 - POLIMENTO SAAS)
# =============================================

def get_user_role():
    """
    Retorna o role do usuário logado.
    Valores possíveis: 'ADMIN', 'OPERADOR'
    Default: 'OPERADOR' (acesso limitado por padrão)
    """
    if not current_user.is_authenticated:
        return None
    return getattr(current_user, 'role', 'OPERADOR')


def is_admin():
    """
    Verifica se o usuário logado é ADMIN da empresa.
    Retorna True apenas se explicitamente configurado como ADMIN.
    """
    return get_user_role() == 'ADMIN'


def is_operador():
    """
    Verifica se o usuário logado é OPERADOR (acesso limitado).
    Retorna True se for OPERADOR ou se não houver role definido.
    """
    return get_user_role() != 'ADMIN'


def admin_required(f):
    """
    Decorator que bloqueia acesso a rotas exclusivas de ADMIN.
    OPERADORES recebem 403 Forbidden com mensagem amigável.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not is_admin():
            abort(403, description="Acesso restrito. Você precisa ser Administrador da empresa para acessar este recurso.")
        return f(*args, **kwargs)
    return decorated_function


# =============================================
# HELPERS DE LIMITES DE PLANO (ETAPA 10)
# =============================================

def get_limite_clientes():
    """Retorna o limite de clientes do plano atual. NULL = ilimitado."""
    from flask import g
    if hasattr(g, 'empresa') and g.empresa:
        return g.empresa.get('limite_clientes', 50)
    return 50


def get_limite_veiculos():
    """Retorna o limite de veículos do plano atual. NULL = ilimitado."""
    from flask import g
    if hasattr(g, 'empresa') and g.empresa:
        return g.empresa.get('limite_veiculos', 50)
    return 50


def get_limite_usuarios():
    """Retorna o limite de usuários do plano atual. NULL = ilimitado."""
    from flask import g
    if hasattr(g, 'empresa') and g.empresa:
        return g.empresa.get('limite_usuarios', 3)
    return 3


def get_plano():
    """Retorna o plano atual da empresa."""
    from flask import g
    if hasattr(g, 'empresa') and g.empresa:
        return g.empresa.get('plano', 'BASICO')
    return 'BASICO'


def verificar_limite_clientes(cursor, empresa_id):
    """
    Verifica se a empresa pode cadastrar mais clientes.
    Retorna (pode_cadastrar, mensagem)
    """
    from flask import g
    
    limite = get_limite_clientes()
    if limite is None:  # Plano ilimitado
        return True, None
    
    # Contar clientes ativos
    cursor.execute("""
        SELECT COUNT(*) FROM clientes 
        WHERE empresa_id = %s AND ativo = true
    """, (empresa_id,))
    total = cursor.fetchone()[0]
    
    if total >= limite:
        return False, f"Limite de {limite} clientes atingido. Faça upgrade do seu plano para cadastrar mais."
    
    return True, None


def verificar_limite_veiculos(cursor, empresa_id):
    """
    Verifica se a empresa pode cadastrar mais veículos.
    Retorna (pode_cadastrar, mensagem)
    """
    limite = get_limite_veiculos()
    if limite is None:  # Plano ilimitado
        return True, None
    
    # Contar veículos ativos
    cursor.execute("""
        SELECT COUNT(*) FROM veiculos 
        WHERE empresa_id = %s AND ativo = true
    """, (empresa_id,))
    total = cursor.fetchone()[0]
    
    if total >= limite:
        return False, f"Limite de {limite} veículos atingido. Faça upgrade do seu plano para cadastrar mais."
    
    return True, None


def verificar_limite_usuarios(cursor, empresa_id):
    """
    Verifica se a empresa pode cadastrar mais usuários.
    Retorna (pode_cadastrar, mensagem)
    """
    limite = get_limite_usuarios()
    if limite is None:  # Plano ilimitado
        return True, None
    
    # Contar usuários ativos
    cursor.execute("""
        SELECT COUNT(*) FROM usuarios 
        WHERE empresa_id = %s AND ativo = true
    """, (empresa_id,))
    total = cursor.fetchone()[0]
    
    if total >= limite:
        return False, f"Limite de {limite} usuários atingido. Faça upgrade do seu plano para cadastrar mais."
    
    return True, None


def contar_recursos_usados(cursor, empresa_id):
    """
    Retorna dicionário com contagem de recursos usados pela empresa.
    Útil para exibir na página Minha Empresa.
    """
    resultado = {
        'clientes': 0,
        'veiculos': 0,
        'usuarios': 0
    }
    
    # Contar clientes
    cursor.execute("""
        SELECT COUNT(*) FROM clientes 
        WHERE empresa_id = %s AND ativo = true
    """, (empresa_id,))
    resultado['clientes'] = cursor.fetchone()[0]
    
    # Contar veículos
    cursor.execute("""
        SELECT COUNT(*) FROM veiculos 
        WHERE empresa_id = %s AND ativo = true
    """, (empresa_id,))
    resultado['veiculos'] = cursor.fetchone()[0]
    
    # Contar usuários
    cursor.execute("""
        SELECT COUNT(*) FROM usuarios 
        WHERE empresa_id = %s AND ativo = true
    """, (empresa_id,))
    resultado['usuarios'] = cursor.fetchone()[0]
    
    return resultado


def get_info_plano():
    """
    Retorna dicionário com informações do plano para exibição.
    """
    plano = get_plano()
    
    info_planos = {
        'BASICO': {
            'nome': 'Básico',
            'cor': 'secondary',
            'icone': 'bi-box',
            'descricao': 'Plano inicial para pequenas operações'
        },
        'PROFISSIONAL': {
            'nome': 'Profissional',
            'cor': 'primary',
            'icone': 'bi-briefcase',
            'descricao': 'Para empresas em crescimento'
        },
        'ENTERPRISE': {
            'nome': 'Enterprise',
            'cor': 'success',
            'icone': 'bi-building',
            'descricao': 'Recursos ilimitados para grandes operações'
        }
    }
    
    return info_planos.get(plano, info_planos['BASICO'])