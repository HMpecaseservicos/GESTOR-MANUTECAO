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


# =============================================
# HELPERS DE NOTIFICAÇÕES (ETAPA 12)
# =============================================

# Tipos de notificação disponíveis
TIPOS_NOTIFICACAO = {
    'LIMITE_AVISO': {'icone': 'fas fa-exclamation-triangle', 'cor': 'warning'},
    'LIMITE_BLOQUEIO': {'icone': 'fas fa-ban', 'cor': 'danger'},
    'MANUTENCAO_ATRASADA': {'icone': 'fas fa-clock', 'cor': 'warning'},
    'SERVICO_SEM_FATURAMENTO': {'icone': 'fas fa-file-invoice-dollar', 'cor': 'info'},
    'USUARIO_CRIADO': {'icone': 'fas fa-user-plus', 'cor': 'success'},
    'ACAO_BLOQUEADA': {'icone': 'fas fa-lock', 'cor': 'danger'},
    'SISTEMA': {'icone': 'fas fa-info-circle', 'cor': 'primary'},
}


def create_notification(empresa_id, tipo, titulo, mensagem, usuario_id=None, link=None):
    """
    Cria uma nova notificação no sistema.
    
    Args:
        empresa_id: ID da empresa (obrigatório)
        tipo: Tipo da notificação (LIMITE_AVISO, MANUTENCAO_ATRASADA, etc.)
        titulo: Título curto (max 200 chars)
        mensagem: Descrição detalhada
        usuario_id: ID do usuário destinatário (None = todos da empresa)
        link: URL para ação (opcional)
    
    Returns:
        int: ID da notificação criada ou None em caso de erro
    """
    from config import Config
    
    if not empresa_id or not titulo:
        return None
    
    try:
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO notificacoes (empresa_id, usuario_id, tipo, titulo, mensagem, link, lida)
                VALUES (%s, %s, %s, %s, %s, %s, false)
                RETURNING id
            """, (empresa_id, usuario_id, tipo, titulo[:200], mensagem, link))
            
            notificacao_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return notificacao_id
        else:
            import sqlite3
            conn = sqlite3.connect('database/frota.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO notificacoes (empresa_id, usuario_id, tipo, titulo, mensagem, link, lida)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (empresa_id, usuario_id, tipo, titulo[:200], mensagem, link))
            
            notificacao_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return notificacao_id
            
    except Exception as e:
        print(f"Erro ao criar notificação: {e}")
        return None


def get_unread_count(empresa_id, usuario_id=None, is_admin=False):
    """
    Retorna o número de notificações não lidas.
    
    Args:
        empresa_id: ID da empresa
        usuario_id: ID do usuário
        is_admin: Se True, conta todas da empresa; se False, apenas do usuário
    
    Returns:
        int: Quantidade de notificações não lidas
    """
    from config import Config
    
    if not empresa_id:
        return 0
    
    try:
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            if is_admin:
                # Admin vê todas da empresa
                cursor.execute("""
                    SELECT COUNT(*) FROM notificacoes 
                    WHERE empresa_id = %s AND lida = false
                """, (empresa_id,))
            else:
                # Operador vê apenas as dele ou gerais (usuario_id IS NULL)
                cursor.execute("""
                    SELECT COUNT(*) FROM notificacoes 
                    WHERE empresa_id = %s AND lida = false
                    AND (usuario_id = %s OR usuario_id IS NULL)
                """, (empresa_id, usuario_id))
            
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count
        else:
            import sqlite3
            conn = sqlite3.connect('database/frota.db')
            cursor = conn.cursor()
            
            if is_admin:
                cursor.execute("""
                    SELECT COUNT(*) FROM notificacoes 
                    WHERE empresa_id = ? AND lida = 0
                """, (empresa_id,))
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM notificacoes 
                    WHERE empresa_id = ? AND lida = 0
                    AND (usuario_id = ? OR usuario_id IS NULL)
                """, (empresa_id, usuario_id))
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
    except Exception as e:
        print(f"Erro ao contar notificações: {e}")
        return 0


def get_recent_notifications(empresa_id, usuario_id=None, is_admin=False, limit=5):
    """
    Retorna as notificações mais recentes.
    
    Args:
        empresa_id: ID da empresa
        usuario_id: ID do usuário
        is_admin: Se True, retorna todas da empresa
        limit: Quantidade máxima de notificações
    
    Returns:
        list: Lista de dicionários com notificações
    """
    from config import Config
    
    if not empresa_id:
        return []
    
    try:
        if Config.IS_POSTGRES:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if is_admin:
                cursor.execute("""
                    SELECT id, tipo, titulo, mensagem, lida, link, created_at
                    FROM notificacoes 
                    WHERE empresa_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (empresa_id, limit))
            else:
                cursor.execute("""
                    SELECT id, tipo, titulo, mensagem, lida, link, created_at
                    FROM notificacoes 
                    WHERE empresa_id = %s
                    AND (usuario_id = %s OR usuario_id IS NULL)
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (empresa_id, usuario_id, limit))
            
            notificacoes = cursor.fetchall()
            cursor.close()
            conn.close()
            return notificacoes
        else:
            import sqlite3
            conn = sqlite3.connect('database/frota.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if is_admin:
                cursor.execute("""
                    SELECT id, tipo, titulo, mensagem, lida, link, created_at
                    FROM notificacoes 
                    WHERE empresa_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (empresa_id, limit))
            else:
                cursor.execute("""
                    SELECT id, tipo, titulo, mensagem, lida, link, created_at
                    FROM notificacoes 
                    WHERE empresa_id = ?
                    AND (usuario_id = ? OR usuario_id IS NULL)
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (empresa_id, usuario_id, limit))
            
            notificacoes = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return notificacoes
            
    except Exception as e:
        print(f"Erro ao buscar notificações: {e}")
        return []


def mark_notification_read(notificacao_id, empresa_id, usuario_id=None, is_admin=False):
    """
    Marca uma notificação como lida.
    
    Returns:
        bool: True se sucesso, False se erro
    """
    from config import Config
    
    if not notificacao_id or not empresa_id:
        return False
    
    try:
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            if is_admin:
                cursor.execute("""
                    UPDATE notificacoes SET lida = true
                    WHERE id = %s AND empresa_id = %s
                """, (notificacao_id, empresa_id))
            else:
                cursor.execute("""
                    UPDATE notificacoes SET lida = true
                    WHERE id = %s AND empresa_id = %s
                    AND (usuario_id = %s OR usuario_id IS NULL)
                """, (notificacao_id, empresa_id, usuario_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        else:
            import sqlite3
            conn = sqlite3.connect('database/frota.db')
            cursor = conn.cursor()
            
            if is_admin:
                cursor.execute("""
                    UPDATE notificacoes SET lida = 1
                    WHERE id = ? AND empresa_id = ?
                """, (notificacao_id, empresa_id))
            else:
                cursor.execute("""
                    UPDATE notificacoes SET lida = 1
                    WHERE id = ? AND empresa_id = ?
                    AND (usuario_id = ? OR usuario_id IS NULL)
                """, (notificacao_id, empresa_id, usuario_id))
            
            conn.commit()
            conn.close()
            return True
            
    except Exception as e:
        print(f"Erro ao marcar notificação como lida: {e}")
        return False


def mark_all_notifications_read(empresa_id, usuario_id=None, is_admin=False):
    """
    Marca todas as notificações como lidas.
    """
    from config import Config
    
    if not empresa_id:
        return False
    
    try:
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            if is_admin:
                cursor.execute("""
                    UPDATE notificacoes SET lida = true
                    WHERE empresa_id = %s AND lida = false
                """, (empresa_id,))
            else:
                cursor.execute("""
                    UPDATE notificacoes SET lida = true
                    WHERE empresa_id = %s AND lida = false
                    AND (usuario_id = %s OR usuario_id IS NULL)
                """, (empresa_id, usuario_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        else:
            import sqlite3
            conn = sqlite3.connect('database/frota.db')
            cursor = conn.cursor()
            
            if is_admin:
                cursor.execute("""
                    UPDATE notificacoes SET lida = 1
                    WHERE empresa_id = ? AND lida = 0
                """, (empresa_id,))
            else:
                cursor.execute("""
                    UPDATE notificacoes SET lida = 1
                    WHERE empresa_id = ? AND lida = 0
                    AND (usuario_id = ? OR usuario_id IS NULL)
                """, (empresa_id, usuario_id))
            
            conn.commit()
            conn.close()
            return True
            
    except Exception as e:
        print(f"Erro ao marcar todas notificações como lidas: {e}")
        return False


def notify_limit_warning(empresa_id, recurso, percentual, atual, limite):
    """
    Cria notificação de aviso de limite.
    
    Args:
        recurso: 'clientes', 'veiculos' ou 'usuarios'
        percentual: Percentual de uso (80, 90, 100)
        atual: Quantidade atual
        limite: Limite do plano
    """
    if percentual >= 100:
        tipo = 'LIMITE_BLOQUEIO'
        titulo = f"Limite de {recurso} atingido!"
        mensagem = f"Você atingiu o limite de {limite} {recurso} do seu plano. Para continuar cadastrando, faça upgrade do plano."
    else:
        tipo = 'LIMITE_AVISO'
        titulo = f"Atenção: {percentual}% do limite de {recurso}"
        mensagem = f"Você está usando {atual} de {limite} {recurso} disponíveis no seu plano. Considere fazer upgrade."
    
    return create_notification(empresa_id, tipo, titulo, mensagem, link='/minha-empresa')


def notify_user_created(empresa_id, admin_id, novo_usuario_nome, novo_usuario_role):
    """
    Notifica sobre criação de novo usuário.
    """
    titulo = f"Novo usuário criado: {novo_usuario_nome}"
    mensagem = f"O usuário {novo_usuario_nome} foi adicionado como {novo_usuario_role}."
    
    return create_notification(empresa_id, 'USUARIO_CRIADO', titulo, mensagem, 
                               usuario_id=admin_id, link='/usuarios')