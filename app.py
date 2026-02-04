"""
════════════════════════════════════════════════════════════════════════════════
                    SISTEMA DE GESTÃO DE MANUTENÇÃO DE FROTA
                              Versão Profissional 2.0
════════════════════════════════════════════════════════════════════════════════

Sistema completo para gerenciamento de manutenção de veículos e máquinas,
incluindo controle de estoque de peças, fornecedores, relatórios e dashboard
analítico com alertas inteligentes.

CARACTERÍSTICAS PRINCIPAIS:
✅ Gestão completa de veículos e manutenções
✅ Controle automático de estoque de peças
✅ Sistema de fornecedores e parceiros
✅ Relatórios em PDF profissionais
✅ Dashboard com métricas e alertas
✅ Interface responsiva e moderna
✅ Chatbot assistente inteligente

TECNOLOGIAS:
- Backend: Flask (Python)
- Frontend: Bootstrap 5 + JavaScript
- Banco: SQLite com triggers e índices
- Relatórios: ReportLab PDF
- UI/UX: Font Awesome + CSS3

DESENVOLVIDO: Outubro 2025
VERSÃO: 2.0.0 Professional
════════════════════════════════════════════════════════════════════════════════
"""

# =============================================
# IMPORTAÇÕES E CONFIGURAÇÕES
# =============================================

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, Response, flash, session, g
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import login_required, current_user, login_user, logout_user
import sqlite3
from datetime import datetime
import os
import traceback
import logging
from logging.handlers import RotatingFileHandler
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import json
import csv
import codecs
from io import StringIO, BytesIO

# Importar módulos personalizados
from config import Config
from auth import login_manager, bcrypt, init_auth_tables, authenticate_user, admin_required, tecnico_required, log_action
from database_manager import db_manager

# =============================================
# CONFIGURAÇÃO DA APLICAÇÃO
# =============================================

app = Flask(__name__)
app.config.from_object(Config)

# Garantir que diretórios existem
Config.ensure_directories()

# Configurações do sistema (compatibilidade)
DATABASE = Config.DATABASE_PATH
REPORTS_DIR = Config.REPORTS_FOLDER
UPLOAD_FOLDER = Config.UPLOAD_FOLDER

# Inicializar extensões de segurança
csrf = CSRFProtect(app)
login_manager.init_app(app)
bcrypt.init_app(app)

# Configurar Rate Limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=Config.RATELIMIT_STORAGE_URL,
    enabled=Config.RATELIMIT_ENABLED
)

# =============================================
# EXECUÇÃO AUTOMÁTICA DE MIGRAÇÕES (POSTGRESQL)
# =============================================

def run_migrations_on_startup():
    """Executa migrações pendentes no startup (PostgreSQL apenas)"""
    import sys as _sys
    if Config.IS_POSTGRES and Config.DATABASE_URL:
        try:
            print("🔧 PostgreSQL detectado - Executando migrações automaticamente...", flush=True)
            _sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'migrations'))
            from migration_manager import MigrationManager
            
            manager = MigrationManager(database_url=Config.DATABASE_URL)
            result = manager.run_pending_migrations()
            if result.get('success'):
                print(f"✅ Migrações concluídas! {result.get('migrations_run', 0)} aplicada(s)", flush=True)
            else:
                print(f"⚠️  Migrações com erro: {result.get('errors', [])}", flush=True)
        except Exception as e:
            print(f"⚠️  Erro ao executar migrações: {e}", flush=True)
            import traceback
            traceback.print_exc()
            _sys.stdout.flush()

# Executar migrações no startup
run_migrations_on_startup()

# Configurar página de login
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'

# Configurar logging
if not app.debug:
    if not os.path.exists(Config.LOG_FOLDER):
        os.mkdir(Config.LOG_FOLDER)
    file_handler = RotatingFileHandler(Config.LOG_FILE, maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Sistema de Gestão de Frota iniciado')

# =============================================
# CONTEXTO GLOBAL - EMPRESA DO USUÁRIO LOGADO
# =============================================

@app.before_request
def load_empresa_context():
    """
    Carrega os dados da empresa do usuário logado no contexto global g.
    Disponibiliza g.empresa com tipo_operacao para uso em toda a aplicação.
    """
    g.empresa = None
    g.tipo_operacao = 'FROTA'  # Default seguro
    
    if current_user.is_authenticated and hasattr(current_user, 'empresa_id') and current_user.empresa_id:
        try:
            if Config.IS_POSTGRES:
                import psycopg2
                conn = psycopg2.connect(Config.DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, nome, tipo_operacao, plano FROM empresas WHERE id = %s",
                    (current_user.empresa_id,)
                )
            else:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, nome, tipo_operacao, plano FROM empresas WHERE id = ?",
                    (current_user.empresa_id,)
                )
            
            row = cursor.fetchone()
            if row:
                g.empresa = {
                    'id': row[0],
                    'nome': row[1],
                    'tipo_operacao': row[2] or 'FROTA',  # Fallback para empresas antigas
                    'plano': row[3]
                }
                g.tipo_operacao = g.empresa['tipo_operacao']
            
            cursor.close()
            conn.close()
        except Exception as e:
            app.logger.warning(f"Erro ao carregar contexto da empresa: {e}")


@app.context_processor
def inject_empresa_context():
    """
    Injeta variáveis de contexto da empresa em todos os templates.
    Permite usar {{ empresa }}, {{ is_frota }}, {{ is_servico }} nos templates.
    """
    from empresa_helpers import is_frota, is_servico
    return {
        'empresa': getattr(g, 'empresa', None),
        'tipo_operacao': getattr(g, 'tipo_operacao', 'FROTA'),
        'is_frota': is_frota(),
        'is_servico': is_servico()
    }

# Handler de erros globais
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Erro interno: {error}')
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

# Filtro personalizado para formatação de moeda brasileira
@app.template_filter('moeda_br')
def moeda_br_filter(valor):
    """Formatar valor como moeda brasileira"""
    if valor is None:
        return 'R$ 0,00'
    try:
        return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return 'R$ 0,00'

# =============================================
# SISTEMA DE BANCO DE DADOS PROFISSIONAL
# =============================================

def get_db_connection(optimize=False):
    """
    Cria uma conexão com o banco de dados
    optimize=True: Aplica otimizações avançadas (use apenas quando necessário)
    """
    conn = sqlite3.connect(DATABASE, timeout=30.0)
    
    if optimize:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA temp_store=MEMORY;')
        conn.execute('PRAGMA mmap_size=268435456;')  # 256MB
    else:
        # Configurações básicas e seguras
        conn.execute('PRAGMA journal_mode=WAL;')
    
    return conn

# Usar database_manager para inicialização
def init_db():
    """Inicializar banco de dados usando database_manager"""
    success = db_manager.init_database()
    if success:
        # Inicializar tabelas de autenticação
        conn = sqlite3.connect(DATABASE)
        init_auth_tables(conn)
        conn.close()
        # Inserir dados de exemplo se necessário
        db_manager.insert_sample_data()
    return success

# =============================================
# ROTAS DE SISTEMA (SEM AUTENTICAÇÃO)
# =============================================

@app.route('/health')
@limiter.exempt
def health_check():
    """
    Endpoint de health check para Fly.io e monitoramento
    Verifica conectividade com banco de dados
    """
    try:
        if Config.IS_POSTGRES:
            # PostgreSQL
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
        else:
            # SQLite
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'db_type': 'PostgreSQL' if Config.IS_POSTGRES else 'SQLite'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'database': 'disconnected'
        }), 503

# =============================================
# ROTAS DE AUTENTICAÇÃO
# =============================================

@app.route('/cadastro', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def cadastro():
    """Rota de auto-cadastro de empresa e usuário"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Dados da empresa
        empresa_nome = request.form.get('empresa_nome', '').strip()
        empresa_cnpj = request.form.get('empresa_cnpj', '').strip()
        empresa_telefone = request.form.get('empresa_telefone', '').strip()
        empresa_email = request.form.get('empresa_email', '').strip()
        plano = request.form.get('plano', 'basico')
        
        # Tipo de operação (ETAPA 1 HÍBRIDO)
        tipo_operacao = request.form.get('tipo_operacao', 'FROTA')
        if tipo_operacao not in ('FROTA', 'SERVICO'):
            tipo_operacao = 'FROTA'  # Fallback seguro
        
        # Dados do usuário
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip().lower()
        telefone = request.form.get('telefone', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validações
        erros = []
        
        if not empresa_nome:
            erros.append('Nome da empresa é obrigatório')
        if not nome:
            erros.append('Seu nome é obrigatório')
        if not email:
            erros.append('Email é obrigatório')
        if not username:
            erros.append('Nome de usuário é obrigatório')
        if len(password) < 6:
            erros.append('Senha deve ter no mínimo 6 caracteres')
        if password != password_confirm:
            erros.append('As senhas não coincidem')
        
        # Verificar se username já existe
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM usuarios WHERE username = ?', (username,))
        if cursor.fetchone():
            erros.append('Este nome de usuário já está em uso')
        
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
        if cursor.fetchone():
            erros.append('Este email já está cadastrado')
        
        if erros:
            for erro in erros:
                flash(erro, 'danger')
            conn.close()
            return render_template('cadastro.html')
        
        try:
            # Definir limites baseado no plano
            limites = {
                'basico': {'veiculos': 10, 'usuarios': 2},
                'profissional': {'veiculos': 50, 'usuarios': 10},
                'enterprise': {'veiculos': 999999, 'usuarios': 999999}
            }
            
            limite = limites.get(plano, limites['basico'])
            
            # Criar a empresa (com tipo_operacao - ETAPA 1 HÍBRIDO)
            cursor.execute('''
                INSERT INTO empresas (nome, cnpj, telefone, email, plano, ativo, 
                                     limite_veiculos, limite_usuarios, tipo_operacao, data_criacao)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, datetime('now'))
            ''', (empresa_nome, empresa_cnpj, empresa_telefone, empresa_email, 
                  plano, limite['veiculos'], limite['usuarios'], tipo_operacao))
            
            empresa_id = cursor.lastrowid
            
            # Criar o usuário administrador
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            
            cursor.execute('''
                INSERT INTO usuarios (username, password_hash, nome, email, telefone, 
                                     role, empresa_id, ativo, data_criacao)
                VALUES (?, ?, ?, ?, ?, 'Admin', ?, 1, datetime('now'))
            ''', (username, password_hash, nome, email, telefone, empresa_id))
            
            conn.commit()
            conn.close()
            
            flash(f'Conta criada com sucesso! Empresa "{empresa_nome}" cadastrada. Faça login para continuar.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Erro ao criar cadastro: {e}")
            flash('Erro ao criar cadastro. Tente novamente.', 'danger')
            return render_template('cadastro.html')
    
    return render_template('cadastro.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Rota de login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user, error = authenticate_user(username, password)
        
        if user:
            login_user(user, remember=remember)
            flash(f'Bem-vindo, {user.username}!', 'success')
            
            # Redirecionar para página solicitada ou dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash(error or 'Usuário ou senha incorretos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Rota de logout"""
    if current_user.is_authenticated:
        log_action(current_user.id, 'LOGOUT', None, None, 'Logout realizado')
    logout_user()
    flash('Você saiu do sistema com sucesso.', 'info')
    return redirect(url_for('login'))


# =============================================
# ROTAS DE CONFIGURAÇÕES DO USUÁRIO
# =============================================

@app.route('/configuracoes')
@login_required
def configuracoes():
    """Página de configurações do usuário"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar dados do usuário
    cursor.execute('SELECT id, username, email, nome, telefone, role, empresa_id FROM usuarios WHERE id = ?', 
                   (current_user.id,))
    row = cursor.fetchone()
    usuario = {
        'id': row[0],
        'username': row[1],
        'email': row[2],
        'nome': row[3],
        'telefone': row[4],
        'role': row[5],
        'empresa_id': row[6]
    }
    
    # Buscar dados da empresa
    empresa = None
    if usuario['empresa_id']:
        cursor.execute('SELECT id, nome, plano FROM empresas WHERE id = ?', (usuario['empresa_id'],))
        emp_row = cursor.fetchone()
        if emp_row:
            empresa = {'id': emp_row[0], 'nome': emp_row[1], 'plano': emp_row[2]}
    
    conn.close()
    return render_template('configuracoes.html', usuario=usuario, empresa=empresa)


@app.route('/atualizar_perfil', methods=['POST'])
@login_required
def atualizar_perfil():
    """Atualizar dados do perfil do usuário"""
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    telefone = request.form.get('telefone', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se email já está em uso por outro usuário
    cursor.execute('SELECT id FROM usuarios WHERE email = ? AND id != ?', (email, current_user.id))
    if cursor.fetchone():
        flash('Este email já está em uso por outro usuário.', 'danger')
        conn.close()
        return redirect(url_for('configuracoes'))
    
    cursor.execute('''
        UPDATE usuarios SET nome = ?, email = ?, telefone = ? WHERE id = ?
    ''', (nome, email, telefone, current_user.id))
    
    conn.commit()
    conn.close()
    
    flash('Perfil atualizado com sucesso!', 'success')
    return redirect(url_for('configuracoes'))


@app.route('/alterar_minha_senha', methods=['POST'])
@login_required
def alterar_minha_senha():
    """Alterar senha do usuário via configurações"""
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    
    if nova_senha != confirmar_senha:
        flash('As senhas não coincidem.', 'danger')
        return redirect(url_for('configuracoes'))
    
    if len(nova_senha) < 6:
        flash('A nova senha deve ter no mínimo 6 caracteres.', 'danger')
        return redirect(url_for('configuracoes'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar senha atual
    cursor.execute('SELECT password_hash FROM usuarios WHERE id = ?', (current_user.id,))
    row = cursor.fetchone()
    
    if not row or not bcrypt.check_password_hash(row[0], senha_atual):
        flash('Senha atual incorreta.', 'danger')
        conn.close()
        return redirect(url_for('configuracoes'))
    
    # Atualizar senha
    nova_hash = bcrypt.generate_password_hash(nova_senha).decode('utf-8')
    cursor.execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (nova_hash, current_user.id))
    
    conn.commit()
    conn.close()
    
    flash('Senha alterada com sucesso!', 'success')
    return redirect(url_for('configuracoes'))


@app.route('/minha-empresa')
@login_required
def minha_empresa():
    """Página de configurações da empresa"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar empresa do usuário
    cursor.execute('''
        SELECT e.* FROM empresas e
        JOIN usuarios u ON u.empresa_id = e.id
        WHERE u.id = ?
    ''', (current_user.id,))
    
    row = cursor.fetchone()
    if not row:
        flash('Empresa não encontrada.', 'warning')
        conn.close()
        return redirect(url_for('dashboard'))
    
    cols = [desc[0] for desc in cursor.description]
    empresa = dict(zip(cols, row))
    
    # Estatísticas da empresa
    empresa_id = empresa['id']
    
    cursor.execute('SELECT COUNT(*) FROM veiculos WHERE empresa_id = ?', (empresa_id,))
    veiculos = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM manutencoes WHERE empresa_id = ?', (empresa_id,))
    manutencoes = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM pecas WHERE empresa_id = ?', (empresa_id,))
    pecas = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM fornecedores WHERE empresa_id = ?', (empresa_id,))
    fornecedores = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tecnicos WHERE empresa_id = ?', (empresa_id,))
    tecnicos = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM usuarios WHERE empresa_id = ?', (empresa_id,))
    usuarios = cursor.fetchone()[0]
    
    conn.close()
    
    stats = {
        'veiculos': veiculos,
        'manutencoes': manutencoes,
        'pecas': pecas,
        'fornecedores': fornecedores,
        'tecnicos': tecnicos,
        'usuarios': usuarios
    }
    
    return render_template('minha_empresa.html', empresa=empresa, stats=stats)


@app.route('/atualizar_minha_empresa', methods=['POST'])
@login_required
def atualizar_minha_empresa():
    """Atualizar dados da empresa do usuário logado"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar empresa do usuário
    cursor.execute('SELECT empresa_id FROM usuarios WHERE id = ?', (current_user.id,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        flash('Empresa não encontrada.', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))
    
    empresa_id = row[0]
    
    nome = request.form.get('nome', '').strip()
    cnpj = request.form.get('cnpj', '').strip()
    telefone = request.form.get('telefone', '').strip()
    email = request.form.get('email', '').strip()
    endereco = request.form.get('endereco', '').strip()
    cidade = request.form.get('cidade', '').strip()
    estado = request.form.get('estado', '').strip()
    cep = request.form.get('cep', '').strip()
    
    cursor.execute('''
        UPDATE empresas 
        SET nome = ?, cnpj = ?, telefone = ?, email = ?, endereco = ?, cidade = ?, estado = ?, cep = ?
        WHERE id = ?
    ''', (nome, cnpj, telefone, email, endereco, cidade, estado, cep, empresa_id))
    
    conn.commit()
    conn.close()
    
    flash('Dados da empresa atualizados com sucesso!', 'success')
    return redirect(url_for('minha_empresa'))


# =============================================
# ROTAS PRINCIPAIS (COM PROTEÇÃO)
# =============================================

@app.route('/')
@login_required
def dashboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Estatísticas gerais
    cursor.execute("SELECT COUNT(*) FROM veiculos")
    total_veiculos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM manutencoes WHERE status = 'Agendada'")
    manutencoes_pendentes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM manutencoes WHERE status = 'Concluída' AND data_realizada >= date('now', '-30 days')")
    manutencoes_30_dias = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tecnicos WHERE status = 'Ativo'")
    tecnicos_ativos = cursor.fetchone()[0]
    
    # Próximas manutenções
    cursor.execute('''
        SELECT v.placa, v.modelo, m.tipo, m.data_agendada 
        FROM manutencoes m 
        JOIN veiculos v ON m.veiculo_id = v.id 
        WHERE m.status = 'Agendada' 
        ORDER BY m.data_agendada 
        LIMIT 5
    ''')
    proximas_manutencoes = cursor.fetchall()
    
    # Alertas de estoque baixo
    cursor.execute("SELECT nome, quantidade_estoque FROM pecas WHERE quantidade_estoque < 3")
    alertas_estoque = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         total_veiculos=total_veiculos,
                         manutencoes_pendentes=manutencoes_pendentes,
                         manutencoes_30_dias=manutencoes_30_dias,
                         tecnicos_ativos=tecnicos_ativos,
                         proximas_manutencoes=proximas_manutencoes,
                         alertas_estoque=alertas_estoque)

@app.route('/veiculos')
@login_required
def veiculos():
    from empresa_helpers import is_servico, get_empresa_id
    
    empresa_id = get_empresa_id()
    veiculos_lista = []
    clientes_lista = []
    
    try:
        if Config.IS_POSTGRES:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Buscar veículos com JOIN para cliente (modo SERVICO)
            cursor.execute('''
                SELECT v.*, COUNT(m.id) as total_manutencoes,
                       c.nome as cliente_nome
                FROM veiculos v 
                LEFT JOIN manutencoes m ON v.id = m.veiculo_id 
                LEFT JOIN clientes c ON v.cliente_id = c.id
                WHERE v.empresa_id = %s
                GROUP BY v.id, c.nome
                ORDER BY v.placa
            ''', (empresa_id,))
            veiculos_lista = cursor.fetchall()
            
            # Buscar clientes ativos para o formulário (apenas SERVICO)
            if is_servico():
                cursor.execute('''
                    SELECT id, nome FROM clientes 
                    WHERE empresa_id = %s AND status = 'ATIVO'
                    ORDER BY nome
                ''', (empresa_id,))
                clientes_lista = cursor.fetchall()
            
            cursor.close()
            conn.close()
        else:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT v.*, COUNT(m.id) as total_manutencoes,
                       c.nome as cliente_nome
                FROM veiculos v 
                LEFT JOIN manutencoes m ON v.id = m.veiculo_id 
                LEFT JOIN clientes c ON v.cliente_id = c.id
                WHERE v.empresa_id = ?
                GROUP BY v.id
                ORDER BY v.placa
            ''', (empresa_id,))
            veiculos_lista = [dict(row) for row in cursor.fetchall()]
            
            if is_servico():
                cursor.execute('''
                    SELECT id, nome FROM clientes 
                    WHERE empresa_id = ? AND status = 'ATIVO'
                    ORDER BY nome
                ''', (empresa_id,))
                clientes_lista = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
    except Exception as e:
        print(f"Erro ao listar veículos: {e}")
        traceback.print_exc()
        flash('Erro ao carregar lista de veículos.', 'danger')
    
    return render_template('veiculos.html', veiculos=veiculos_lista, clientes=clientes_lista)

@app.route('/api/veiculos', methods=['GET'])
@login_required
def api_veiculos():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, tipo, marca, modelo, placa, ano, quilometragem, proxima_manutencao, status
            FROM veiculos 
            ORDER BY placa
        ''')
        
        veiculos = []
        for row in cursor.fetchall():
            veiculos.append({
                'id': row[0],
                'tipo': row[1],
                'marca': row[2],
                'modelo': row[3],
                'placa': row[4],
                'ano': row[5],
                'quilometragem': row[6],
                'proxima_manutencao': row[7],
                'status': row[8]
            })
        
        conn.close()
        return jsonify(veiculos)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/veiculo/<int:veiculo_id>')
@login_required
def detalhes_veiculo(veiculo_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM veiculos WHERE id = ?", (veiculo_id,))
    veiculo = cursor.fetchone()
    
    cursor.execute("SELECT * FROM manutencoes WHERE veiculo_id = ? ORDER BY data_agendada DESC", (veiculo_id,))
    manutencoes = cursor.fetchall()
    
    # Busca a próxima manutenção agendada (status='Agendada' e data >= hoje)
    cursor.execute("""
        SELECT data_agendada 
        FROM manutencoes 
        WHERE veiculo_id = ? 
        AND status = 'Agendada' 
        AND date(data_agendada) >= date('now')
        ORDER BY data_agendada ASC 
        LIMIT 1
    """, (veiculo_id,))
    proxima_manutencao = cursor.fetchone()
    proxima_data = proxima_manutencao[0] if proxima_manutencao else None
    
    cursor.execute('''
        SELECT DISTINCT p.*, f.nome as fornecedor_nome 
        FROM pecas p 
        JOIN fornecedores f ON p.fornecedor_id = f.id 
        JOIN manutencao_pecas mp ON p.id = mp.peca_id
        JOIN manutencoes m ON mp.manutencao_id = m.id
        WHERE m.veiculo_id = ?
        ORDER BY p.nome
    ''', (veiculo_id,))
    pecas_compativeis = cursor.fetchall()
    
    # Busca técnicos e fornecedores para o modal de agendamento
    cursor.execute("SELECT * FROM tecnicos ORDER BY nome")
    tecnicos = cursor.fetchall()
    
    cursor.execute("SELECT * FROM fornecedores WHERE especialidade LIKE '%serviço%' OR especialidade LIKE '%Serviço%' ORDER BY nome")
    fornecedores_servicos = cursor.fetchall()
    
    conn.close()
    
    return render_template('detalhes_veiculo.html', 
                         veiculo=veiculo, 
                         manutencoes=manutencoes, 
                         pecas_compativeis=pecas_compativeis,
                         tecnicos=tecnicos,
                         fornecedores_servicos=fornecedores_servicos,
                         proxima_manutencao=proxima_data)

@app.route('/api/veiculo', methods=['POST'])
@login_required
def criar_veiculo():
    """Criar novo veículo"""
    from empresa_helpers import is_servico, get_empresa_id
    
    try:
        data = request.json
        empresa_id = get_empresa_id()
        cliente_id = data.get('cliente_id') or None
        
        # Validação para modo SERVICO: cliente_id obrigatório
        if is_servico():
            if not cliente_id:
                return jsonify({
                    'success': False,
                    'message': 'Para empresas de serviço, é obrigatório selecionar um cliente!'
                }), 400
        else:
            # Modo FROTA: cliente_id deve ser NULL
            cliente_id = None
        
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            # Validar placa única na empresa
            cursor.execute("SELECT id FROM veiculos WHERE placa = %s AND empresa_id = %s", 
                          (data.get('placa'), empresa_id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Placa já cadastrada no sistema!'
                }), 400
            
            # Validar que cliente pertence à empresa (modo SERVICO)
            if cliente_id:
                cursor.execute("SELECT id FROM clientes WHERE id = %s AND empresa_id = %s", 
                              (cliente_id, empresa_id))
                if not cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'Cliente inválido ou não pertence à sua empresa!'
                    }), 400
            
            cursor.execute('''
                INSERT INTO veiculos (empresa_id, tipo, marca, modelo, placa, ano, quilometragem, 
                                      proxima_manutencao, status, cliente_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                empresa_id,
                data.get('tipo'),
                data.get('marca'), 
                data.get('modelo'),
                data.get('placa'),
                data.get('ano'),
                data.get('quilometragem', 0),
                data.get('proxima_manutencao') or None,
                'Operacional',
                cliente_id
            ))
            
            veiculo_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
        else:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            # Validar placa única na empresa
            cursor.execute("SELECT id FROM veiculos WHERE placa = ? AND empresa_id = ?", 
                          (data.get('placa'), empresa_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Placa já cadastrada no sistema!'
                }), 400
            
            # Validar cliente (modo SERVICO)
            if cliente_id:
                cursor.execute("SELECT id FROM clientes WHERE id = ? AND empresa_id = ?", 
                              (cliente_id, empresa_id))
                if not cursor.fetchone():
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'Cliente inválido ou não pertence à sua empresa!'
                    }), 400
            
            cursor.execute('''
                INSERT INTO veiculos (empresa_id, tipo, marca, modelo, placa, ano, quilometragem, 
                                      proxima_manutencao, status, cliente_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                empresa_id,
                data.get('tipo'),
                data.get('marca'), 
                data.get('modelo'),
                data.get('placa'),
                data.get('ano'),
                data.get('quilometragem', 0),
                data.get('proxima_manutencao') or None,
                'Operacional',
                cliente_id
            ))
            
            veiculo_id = cursor.lastrowid
            conn.commit()
            conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Veículo cadastrado com sucesso!',
            'id': veiculo_id
        })
        
    except Exception as e:
        print(f"Erro ao criar veículo: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao criar veículo: {str(e)}'
        }), 500

@app.route('/api/veiculo/<int:veiculo_id>', methods=['PUT'])
@login_required
def editar_veiculo(veiculo_id):
    """Editar veículo existente"""
    from empresa_helpers import is_servico, get_empresa_id
    
    try:
        data = request.json
        empresa_id = get_empresa_id()
        cliente_id = data.get('cliente_id') or None
        
        # Validação para modo SERVICO: cliente_id obrigatório
        if is_servico():
            if not cliente_id:
                return jsonify({
                    'success': False,
                    'message': 'Para empresas de serviço, é obrigatório selecionar um cliente!'
                }), 400
        else:
            # Modo FROTA: cliente_id deve ser NULL
            cliente_id = None
        
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            # Verificar se veículo existe e pertence à empresa
            cursor.execute("SELECT id FROM veiculos WHERE id = %s AND empresa_id = %s", 
                          (veiculo_id, empresa_id))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Veículo não encontrado!'
                }), 404
            
            # Validar placa única (exceto o próprio veículo)
            cursor.execute("SELECT id FROM veiculos WHERE placa = %s AND id != %s AND empresa_id = %s", 
                          (data.get('placa'), veiculo_id, empresa_id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Placa já cadastrada para outro veículo!'
                }), 400
            
            # Validar cliente (modo SERVICO)
            if cliente_id:
                cursor.execute("SELECT id FROM clientes WHERE id = %s AND empresa_id = %s", 
                              (cliente_id, empresa_id))
                if not cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'Cliente inválido ou não pertence à sua empresa!'
                    }), 400
            
            cursor.execute('''
                UPDATE veiculos 
                SET tipo=%s, marca=%s, modelo=%s, placa=%s, ano=%s, quilometragem=%s, 
                    proxima_manutencao=%s, cliente_id=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND empresa_id=%s
            ''', (
                data.get('tipo'),
                data.get('marca'), 
                data.get('modelo'),
                data.get('placa'),
                data.get('ano'),
                data.get('quilometragem', 0),
                data.get('proxima_manutencao') or None,
                cliente_id,
                veiculo_id,
                empresa_id
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        else:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            # Verificar se veículo existe e pertence à empresa
            cursor.execute("SELECT id FROM veiculos WHERE id = ? AND empresa_id = ?", 
                          (veiculo_id, empresa_id))
            if not cursor.fetchone():
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Veículo não encontrado!'
                }), 404
            
            # Validar placa única (exceto o próprio veículo)
            cursor.execute("SELECT id FROM veiculos WHERE placa = ? AND id != ? AND empresa_id = ?", 
                          (data.get('placa'), veiculo_id, empresa_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Placa já cadastrada para outro veículo!'
                }), 400
            
            # Validar cliente (modo SERVICO)
            if cliente_id:
                cursor.execute("SELECT id FROM clientes WHERE id = ? AND empresa_id = ?", 
                              (cliente_id, empresa_id))
                if not cursor.fetchone():
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'Cliente inválido ou não pertence à sua empresa!'
                    }), 400
            
            cursor.execute('''
                UPDATE veiculos 
                SET tipo=?, marca=?, modelo=?, placa=?, ano=?, quilometragem=?, 
                    proxima_manutencao=?, cliente_id=?
                WHERE id=? AND empresa_id=?
            ''', (
                data.get('tipo'),
                data.get('marca'), 
                data.get('modelo'),
                data.get('placa'),
                data.get('ano'),
                data.get('quilometragem', 0),
                data.get('proxima_manutencao') or None,
                cliente_id,
                veiculo_id,
                empresa_id
            ))
            
            conn.commit()
            conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Veículo atualizado com sucesso!'
        })
        
    except Exception as e:
        print(f"Erro ao editar veículo: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao editar veículo: {str(e)}'
        }), 500

@app.route('/api/veiculo/<int:veiculo_id>', methods=['GET'])
@login_required
def obter_veiculo(veiculo_id):
    """Obter dados de um veículo específico"""
    from empresa_helpers import get_empresa_id
    
    try:
        empresa_id = get_empresa_id()
        
        if Config.IS_POSTGRES:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT v.*, c.nome as cliente_nome
                FROM veiculos v
                LEFT JOIN clientes c ON v.cliente_id = c.id
                WHERE v.id = %s AND v.empresa_id = %s
            """, (veiculo_id, empresa_id))
            veiculo = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if veiculo:
                return jsonify({
                    'success': True,
                    'veiculo': {
                        'id': veiculo['id'],
                        'tipo': veiculo['tipo'],
                        'marca': veiculo['marca'],
                        'modelo': veiculo['modelo'],
                        'placa': veiculo['placa'],
                        'ano': veiculo['ano'],
                        'quilometragem': veiculo['quilometragem'],
                        'proxima_manutencao': str(veiculo['proxima_manutencao']) if veiculo['proxima_manutencao'] else None,
                        'status': veiculo['status'],
                        'cliente_id': veiculo['cliente_id'],
                        'cliente_nome': veiculo['cliente_nome']
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Veículo não encontrado!'
                }), 404
        else:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT v.*, c.nome as cliente_nome
                FROM veiculos v
                LEFT JOIN clientes c ON v.cliente_id = c.id
                WHERE v.id = ? AND v.empresa_id = ?
            """, (veiculo_id, empresa_id))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                veiculo = dict(row)
                return jsonify({
                    'success': True,
                    'veiculo': {
                        'id': veiculo['id'],
                        'tipo': veiculo['tipo'],
                        'marca': veiculo['marca'],
                        'modelo': veiculo['modelo'],
                        'placa': veiculo['placa'],
                        'ano': veiculo['ano'],
                        'quilometragem': veiculo['quilometragem'],
                        'proxima_manutencao': veiculo['proxima_manutencao'],
                        'status': veiculo['status'],
                        'cliente_id': veiculo.get('cliente_id'),
                        'cliente_nome': veiculo.get('cliente_nome')
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Veículo não encontrado!'
                }), 404
            
    except Exception as e:
        print(f"Erro ao obter veículo: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao obter veículo: {str(e)}'
        }), 500

@app.route('/api/veiculo/<int:veiculo_id>', methods=['DELETE'])
@login_required
def excluir_veiculo(veiculo_id):
    """Excluir um veículo"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verificar se o veículo tem manutenções associadas
        cursor.execute("SELECT COUNT(*) FROM manutencoes WHERE veiculo_id = ?", (veiculo_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Não é possível excluir este veículo pois possui {count} manutenção(ões) registrada(s)!'
            }), 400
        
        # Excluir o veículo
        cursor.execute("DELETE FROM veiculos WHERE id = ?", (veiculo_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Veículo excluído com sucesso!'
        })
        
    except Exception as e:
        print(f"Erro ao excluir veículo: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao excluir veículo!'
        }), 500

@app.route('/manutencao')
@login_required
def manutencao():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Buscar manutenções com telefone de técnicos OU fornecedores
    cursor.execute('''
        SELECT 
            m.*, 
            v.placa, 
            v.modelo, 
            COALESCE(t.telefone, f.telefone) as telefone
        FROM manutencoes m 
        JOIN veiculos v ON m.veiculo_id = v.id 
        LEFT JOIN tecnicos t ON m.tecnico = t.nome
        LEFT JOIN fornecedores f ON m.tecnico = f.nome
        ORDER BY m.id DESC
    ''')
    manutencoes = cursor.fetchall()
    
    cursor.execute("SELECT id, placa, modelo FROM veiculos")
    veiculos = cursor.fetchall()
    
    cursor.execute("SELECT id, nome FROM tecnicos WHERE status='Ativo' ORDER BY nome")
    tecnicos = cursor.fetchall()
    
    # Buscar TODOS os fornecedores que prestam serviços (especialidade contém 'Serviço' ou 'serviço')
    cursor.execute("SELECT id, nome, telefone FROM fornecedores WHERE especialidade LIKE '%serviço%' OR especialidade LIKE '%Serviço%' ORDER BY nome")
    fornecedores_servicos = cursor.fetchall()
    
    conn.close()
    return render_template('manutencao.html', 
                         manutencoes=manutencoes, 
                         veiculos=veiculos, 
                         tecnicos=tecnicos,
                         fornecedores_servicos=fornecedores_servicos)

@app.route('/api/manutencao', methods=['POST'])
@login_required
def criar_manutencao():
    data = request.json
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO manutencoes (veiculo_id, tipo, descricao, data_agendada, tecnico, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['veiculo_id'], data['tipo'], data['descricao'], data['data_agendada'], data['tecnico'], 'Agendada'))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Rota para obter dados de uma manutenção específica
@app.route('/manutencao/get/<int:manutencao_id>')
@login_required
def get_manutencao(manutencao_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, v.placa, v.modelo 
            FROM manutencoes m 
            JOIN veiculos v ON m.veiculo_id = v.id
            WHERE m.id=?
        ''', (manutencao_id,))
        manutencao = cursor.fetchone()
        
        # Buscar peças utilizadas na manutenção
        cursor.execute('''
            SELECT mp.id, mp.manutencao_id, mp.peca_id, mp.quantidade, mp.preco_unitario,
                   p.nome, p.codigo, (mp.quantidade * mp.preco_unitario) as subtotal
            FROM manutencao_pecas mp
            JOIN pecas p ON mp.peca_id = p.id
            WHERE mp.manutencao_id = ?
            ORDER BY mp.id DESC
        ''', (manutencao_id,))
        pecas_utilizadas = cursor.fetchall()
        
        conn.close()
        
        if manutencao:
            # Calcular total das peças
            total_pecas = sum(float(peca[7]) for peca in pecas_utilizadas) if pecas_utilizadas else 0
            
            return jsonify({
                'success': True,
                'manutencao': {
                    'id': manutencao[0],
                    'veiculo_id': manutencao[1],
                    'tipo': manutencao[2],
                    'descricao': manutencao[3],
                    'data_agendada': manutencao[4],
                    'data_realizada': manutencao[5],
                    'custo': manutencao[6],
                    'status': manutencao[7],
                    'tecnico': manutencao[8],
                    'veiculo_placa': manutencao[9],
                    'veiculo_modelo': manutencao[10]
                },
                'pecas_utilizadas': [
                    {
                        'id': peca[0],
                        'quantidade': peca[3],
                        'preco_unitario': peca[4],
                        'nome': peca[5],
                        'codigo': peca[6],
                        'subtotal': peca[7]
                    } for peca in pecas_utilizadas
                ],
                'total_pecas': total_pecas
            })
        else:
            return jsonify({'success': False, 'message': 'Manutenção não encontrada'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rota para atualizar status da manutenção
@app.route('/manutencao/status/<int:manutencao_id>', methods=['PUT'])
@login_required
def atualizar_status_manutencao(manutencao_id):
    try:
        data = request.json
        novo_status = data.get('status')
        
        if not novo_status:
            return jsonify({'success': False, 'message': 'Status não fornecido'})
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE manutencoes 
            SET status = ?
            WHERE id = ?
        ''', (novo_status, manutencao_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Status atualizado com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rota para editar manutenção
@app.route('/manutencao/edit/<int:manutencao_id>', methods=['POST'])
@login_required
def edit_manutencao(manutencao_id):
    try:
        veiculo_id = request.form['veiculo_id']
        tipo = request.form['tipo']
        descricao = request.form['descricao']
        data_agendada = request.form['data_agendada']
        data_realizada = request.form.get('data_realizada', None)
        custo = request.form.get('custo', None)
        status = request.form['status']
        tecnico = request.form['tecnico']
        
        # Converter campos vazios para None
        if data_realizada == '':
            data_realizada = None
        if custo == '':
            custo = None
        else:
            custo = float(custo) if custo else None
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verificar se a manutenção foi concluída e tem custo
        cursor.execute('SELECT status, custo FROM manutencoes WHERE id = ?', (manutencao_id,))
        manutencao_atual = cursor.fetchone()
        
        cursor.execute('''
            UPDATE manutencoes 
            SET veiculo_id=?, tipo=?, descricao=?, data_agendada=?, data_realizada=?, custo=?, status=?, tecnico=?
            WHERE id=?
        ''', (veiculo_id, tipo, descricao, data_agendada, data_realizada, custo, status, tecnico, manutencao_id))
        
        # Gerar despesa automática se manutenção foi concluída com custo
        if status == 'Concluída' and custo and custo > 0:
            # Verificar se já existe despesa para esta manutenção
            cursor.execute('SELECT id FROM despesas WHERE manutencao_id = ?', (manutencao_id,))
            despesa_existente = cursor.fetchone()
            
            if not despesa_existente:
                # Buscar categoria "Manutenção"
                cursor.execute('SELECT id FROM categorias_despesa WHERE nome = ?', ('Manutenção',))
                categoria_manutencao = cursor.fetchone()
                categoria_id = categoria_manutencao[0] if categoria_manutencao else None
                
                # Criar despesa automática
                data_despesa = data_realizada if data_realizada else data_agendada
                descricao_despesa = f"Manutenção {tipo}: {descricao}"
                
                cursor.execute('''
                    INSERT INTO despesas (descricao, valor, data_despesa, categoria_id, veiculo_id, tipo, manutencao_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (descricao_despesa, custo, data_despesa, categoria_id, veiculo_id, 'Automática', manutencao_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Manutenção atualizada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rota para deletar manutenção
@app.route('/manutencao/delete/<int:manutencao_id>', methods=['DELETE'])
@login_required
def delete_manutencao(manutencao_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM manutencoes WHERE id=?', (manutencao_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Manutenção excluída com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rota para atualizar status da manutenção
@app.route('/manutencao/status/<int:manutencao_id>', methods=['POST'])
@login_required
def update_status_manutencao(manutencao_id):
    try:
        novo_status = request.form['status']
        data_realizada = None
        
        # Se está finalizando, definir data de realização
        if novo_status == 'Concluída':
            from datetime import datetime
            data_realizada = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE manutencoes 
            SET status=?, data_realizada=?
            WHERE id=?
        ''', (novo_status, data_realizada, manutencao_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Status atualizado para {novo_status}!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rotas para gerenciar peças nas manutenções
@app.route('/manutencao/<int:manutencao_id>/pecas')
@login_required
def get_pecas_manutencao(manutencao_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT mp.id, mp.manutencao_id, mp.peca_id, mp.quantidade, mp.preco_unitario, 
               p.nome, p.codigo, p.preco,
               (mp.quantidade * mp.preco_unitario) as subtotal
        FROM manutencao_pecas mp
        JOIN pecas p ON mp.peca_id = p.id
        WHERE mp.manutencao_id = ?
        ORDER BY mp.id DESC
    ''', (manutencao_id,))
    pecas_utilizadas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(pecas_utilizadas)

@app.route('/manutencao/<int:manutencao_id>/pecas/disponiveis')
@login_required
def get_pecas_disponiveis(manutencao_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Buscar informações do veículo da manutenção
    cursor.execute('''
        SELECT v.modelo, v.marca, v.tipo
        FROM manutencoes m
        JOIN veiculos v ON m.veiculo_id = v.id
        WHERE m.id = ?
    ''', (manutencao_id,))
    veiculo = cursor.fetchone()
    
    # Buscar TODAS as peças com estoque disponível
    # Priorizar peças compatíveis, mas mostrar todas
    if veiculo:
        marca = veiculo[1].lower()
        modelo = veiculo[0].lower()
        tipo = veiculo[2].lower()
        
        cursor.execute('''
            SELECT p.*, f.nome as fornecedor_nome,
                   CASE 
                       WHEN LOWER(p.veiculo_compativel) = 'universal' THEN 1
                       WHEN LOWER(p.veiculo_compativel) LIKE ? THEN 2
                       WHEN LOWER(p.veiculo_compativel) LIKE ? THEN 3
                       WHEN LOWER(p.veiculo_compativel) LIKE ? THEN 4
                       ELSE 5
                   END as prioridade
            FROM pecas p
            JOIN fornecedores f ON p.fornecedor_id = f.id
            WHERE p.quantidade_estoque > 0
            ORDER BY prioridade, p.nome
        ''', (f'%{marca}%', f'%{modelo}%', f'%{tipo}%'))
    else:
        # Se não conseguir identificar veículo, mostrar todas com estoque
        cursor.execute('''
            SELECT p.*, f.nome as fornecedor_nome, 1 as prioridade
            FROM pecas p
            JOIN fornecedores f ON p.fornecedor_id = f.id
            WHERE p.quantidade_estoque > 0
            ORDER BY p.nome
        ''')
    
    pecas_disponiveis = cursor.fetchall()
    conn.close()
    
    # Remover a coluna de prioridade do resultado (última coluna)
    pecas_clean = [peca[:-1] for peca in pecas_disponiveis]
    
    return jsonify(pecas_clean)

@app.route('/manutencao/<int:manutencao_id>/pecas/buscar')
@login_required
def buscar_pecas_manutencao(manutencao_id):
    """Buscar peças por nome ou código para adicionar em manutenção"""
    search_term = request.args.get('q', '').strip()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if search_term:
        # Buscar por nome, código ou compatibilidade
        cursor.execute('''
            SELECT p.*, f.nome as fornecedor_nome
            FROM pecas p
            JOIN fornecedores f ON p.fornecedor_id = f.id
            WHERE p.quantidade_estoque > 0
            AND (
                LOWER(p.nome) LIKE ? OR 
                LOWER(p.codigo) LIKE ? OR
                LOWER(p.veiculo_compativel) LIKE ?
            )
            ORDER BY 
                CASE 
                    WHEN LOWER(p.nome) LIKE ? THEN 1
                    WHEN LOWER(p.codigo) LIKE ? THEN 2
                    ELSE 3
                END,
                p.nome
        ''', (f'%{search_term.lower()}%', f'%{search_term.lower()}%', f'%{search_term.lower()}%',
              f'%{search_term.lower()}%', f'%{search_term.lower()}%'))
    else:
        # Se não há termo de busca, retornar todas com estoque
        cursor.execute('''
            SELECT p.*, f.nome as fornecedor_nome
            FROM pecas p
            JOIN fornecedores f ON p.fornecedor_id = f.id
            WHERE p.quantidade_estoque > 0
            ORDER BY p.nome
        ''')
    
    pecas = cursor.fetchall()
    conn.close()
    
    return jsonify(pecas)

@app.route('/manutencao/<int:manutencao_id>/pecas/adicionar', methods=['POST'])
@login_required
def adicionar_peca_manutencao(manutencao_id):
    conn = None
    try:
        data = request.json
        peca_id = data['peca_id']
        quantidade = int(data['quantidade'])
        
        print(f"DEBUG: Adicionando peça {peca_id} (qtd: {quantidade}) à manutenção {manutencao_id}")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verificar se há estoque suficiente
        cursor.execute('SELECT quantidade_estoque, preco FROM pecas WHERE id = ?', (peca_id,))
        peca = cursor.fetchone()
        
        if not peca:
            return jsonify({'success': False, 'message': 'Peça não encontrada!'})
        
        estoque_atual, preco = peca
        if estoque_atual < quantidade:
            return jsonify({'success': False, 'message': f'Estoque insuficiente! Disponível: {estoque_atual}'})
        
        # Adicionar peça à manutenção
        print(f"DEBUG: Inserindo na tabela manutencao_pecas")
        print(f"DEBUG: Valores - manutencao_id={manutencao_id}, peca_id={peca_id}, quantidade={quantidade}, preco={preco}")
        cursor.execute('''
            INSERT INTO manutencao_pecas (manutencao_id, peca_id, quantidade, preco_unitario)
            VALUES (?, ?, ?, ?)
        ''', (manutencao_id, peca_id, quantidade, preco))
        print(f"DEBUG: INSERT bem sucedido!")
        
        # Dar baixa no estoque
        print(f"DEBUG: Atualizando estoque")
        cursor.execute('''
            UPDATE pecas SET quantidade_estoque = quantidade_estoque - ?
            WHERE id = ?
        ''', (quantidade, peca_id))
        
        try:
            # Gerar despesa automática para a peça (opcional - não bloqueia se falhar)
            cursor.execute('SELECT nome FROM pecas WHERE id = ?', (peca_id,))
            nome_peca = cursor.fetchone()[0]
            
            cursor.execute('SELECT veiculo_id, data_realizada, data_agendada FROM manutencoes WHERE id = ?', (manutencao_id,))
            manutencao_info = cursor.fetchone()
            veiculo_id, data_realizada, data_agendada = manutencao_info
            
            # Buscar categoria "Peças e Componentes"
            cursor.execute('SELECT id FROM categorias_despesa WHERE nome = ?', ('Peças e Componentes',))
            categoria_peca = cursor.fetchone()
            categoria_id = categoria_peca[0] if categoria_peca else None
            
            # Criar despesa automática para a peça
            valor_total = preco * quantidade
            data_despesa = data_realizada if data_realizada else data_agendada
            descricao_despesa = f"Peça: {nome_peca} (Qtd: {quantidade})"
            
            cursor.execute('''
                INSERT INTO despesas (descricao, valor, data_despesa, categoria_id, veiculo_id, tipo, manutencao_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (descricao_despesa, valor_total, data_despesa, categoria_id, veiculo_id, 'Automática', manutencao_id))
            print(f"DEBUG: Despesa automática criada")
        except Exception as despesa_error:
            print(f"DEBUG: Erro ao criar despesa (não crítico): {despesa_error}")
            # Continua mesmo se falhar ao criar despesa
        
        print(f"DEBUG: Fazendo commit")
        conn.commit()
        print(f"DEBUG: Peça adicionada com sucesso!")
        
        return jsonify({'success': True, 'message': f'Peça adicionada com sucesso! Estoque atualizado.'})
    except Exception as e:
        print(f"DEBUG ERRO: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        if conn:
            conn.close()

@app.route('/manutencao/<int:manutencao_id>/pecas/<int:item_id>/remover', methods=['DELETE'])
@login_required
def remover_peca_manutencao(manutencao_id, item_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Buscar informações da peça para devolver ao estoque
        cursor.execute('''
            SELECT peca_id, quantidade
            FROM manutencao_pecas
            WHERE id = ? AND manutencao_id = ?
        ''', (item_id, manutencao_id))
        
        item = cursor.fetchone()
        if not item:
            return jsonify({'success': False, 'message': 'Item não encontrado!'})
        
        peca_id, quantidade = item
        
        # Devolver ao estoque
        cursor.execute('''
            UPDATE pecas SET quantidade_estoque = quantidade_estoque + ?
            WHERE id = ?
        ''', (quantidade, peca_id))
        
        # Remover da manutenção
        cursor.execute('''
            DELETE FROM manutencao_pecas
            WHERE id = ? AND manutencao_id = ?
        ''', (item_id, manutencao_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Peça removida e estoque atualizado!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/pecas')
@login_required
def pecas():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, f.nome as fornecedor_nome, f.telefone as fornecedor_telefone, f.email as fornecedor_email
        FROM pecas p 
        JOIN fornecedores f ON p.fornecedor_id = f.id
    ''')
    pecas = cursor.fetchall()
    
    # Buscar fornecedores para os selects
    cursor.execute("SELECT * FROM fornecedores")
    fornecedores = cursor.fetchall()
    
    conn.close()
    return render_template('pecas.html', pecas=pecas, fornecedores=fornecedores)

# Rota para adicionar nova peça
@app.route('/pecas/add', methods=['POST'])
@login_required
def add_peca():
    try:
        nome = request.form['nome']
        codigo = request.form['codigo']
        veiculo_compativel = request.form['veiculo_compativel']
        preco = float(request.form['preco'])
        quantidade_estoque = int(request.form['quantidade_estoque'])
        fornecedor_id = int(request.form['fornecedor_id'])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pecas (nome, codigo, veiculo_compativel, preco, quantidade_estoque, fornecedor_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nome, codigo, veiculo_compativel, preco, quantidade_estoque, fornecedor_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Peça adicionada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rota para editar peça
@app.route('/pecas/edit/<int:peca_id>', methods=['POST'])
@login_required
def edit_peca(peca_id):
    try:
        nome = request.form['nome']
        codigo = request.form['codigo']
        veiculo_compativel = request.form['veiculo_compativel']
        preco = float(request.form['preco'])
        quantidade_estoque = int(request.form['quantidade_estoque'])
        fornecedor_id = int(request.form['fornecedor_id'])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pecas 
            SET nome=?, codigo=?, veiculo_compativel=?, preco=?, quantidade_estoque=?, fornecedor_id=?
            WHERE id=?
        ''', (nome, codigo, veiculo_compativel, preco, quantidade_estoque, fornecedor_id, peca_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Peça atualizada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rota para deletar peça
@app.route('/pecas/delete/<int:peca_id>', methods=['DELETE'])
@login_required
def delete_peca(peca_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pecas WHERE id=?', (peca_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Peça excluída com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rota para ajustar estoque
@app.route('/pecas/estoque/<int:peca_id>', methods=['POST'])
@login_required
def ajustar_estoque(peca_id):
    try:
        nova_quantidade = int(request.form['quantidade'])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('UPDATE pecas SET quantidade_estoque=? WHERE id=?', (nova_quantidade, peca_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Estoque atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rota para obter dados de uma peça específica
@app.route('/pecas/get/<int:peca_id>')
@login_required
def get_peca(peca_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, f.nome as fornecedor_nome 
            FROM pecas p 
            JOIN fornecedores f ON p.fornecedor_id = f.id
            WHERE p.id=?
        ''', (peca_id,))
        peca = cursor.fetchone()
        conn.close()
        
        if peca:
            return jsonify({
                'success': True,
                'peca': {
                    'id': peca[0],
                    'nome': peca[1],
                    'codigo': peca[2],
                    'veiculo_compativel': peca[3],
                    'preco': peca[4],
                    'fornecedor_id': peca[5],
                    'quantidade_estoque': peca[6],
                    'fornecedor_nome': peca[7],
                    'descricao': ''  # Campo não existe na tabela atual
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Peça não encontrada'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# =============================================
# ROTAS - GESTÃO DE EMPRESAS (MULTI-EMPRESA)
# =============================================

@app.route('/empresas')
@login_required
@admin_required
def empresas():
    """Página de gestão de empresas"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM empresas ORDER BY nome")
    empresas = cursor.fetchall()
    conn.close()
    return render_template('empresas.html', empresas=empresas)

@app.route('/api/empresas', methods=['POST'])
@login_required
@admin_required
def criar_empresa():
    """Criar nova empresa"""
    try:
        data = request.json
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO empresas (
                nome, nome_fantasia, cnpj, telefone, email,
                endereco, cidade, estado, cep, plano,
                limite_veiculos, limite_usuarios, ativo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            data.get('nome'),
            data.get('nome_fantasia'),
            data.get('cnpj'),
            data.get('telefone'),
            data.get('email'),
            data.get('endereco'),
            data.get('cidade'),
            data.get('estado'),
            data.get('cep'),
            data.get('plano', 'Básico'),
            data.get('limite_veiculos', 10),
            data.get('limite_usuarios', 3)
        ))
        
        empresa_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_action(f'Criou empresa: {data.get("nome")} (ID: {empresa_id})')
        
        return jsonify({
            'success': True,
            'message': 'Empresa criada com sucesso!',
            'empresa_id': empresa_id
        })
        
    except Exception as e:
        print(f"Erro ao criar empresa: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/empresas/<int:empresa_id>', methods=['PUT'])
@login_required
@admin_required
def atualizar_empresa(empresa_id):
    """Atualizar empresa"""
    try:
        data = request.json
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Atualizar apenas o campo ativo ou todos os campos
        if 'ativo' in data and len(data) == 1:
            cursor.execute('''
                UPDATE empresas SET ativo = ?
                WHERE id = ?
            ''', (data['ativo'], empresa_id))
        else:
            cursor.execute('''
                UPDATE empresas SET
                    nome = ?, nome_fantasia = ?, cnpj = ?,
                    telefone = ?, email = ?, endereco = ?,
                    cidade = ?, estado = ?, cep = ?,
                    plano = ?, limite_veiculos = ?, limite_usuarios = ?
                WHERE id = ?
            ''', (
                data.get('nome'),
                data.get('nome_fantasia'),
                data.get('cnpj'),
                data.get('telefone'),
                data.get('email'),
                data.get('endereco'),
                data.get('cidade'),
                data.get('estado'),
                data.get('cep'),
                data.get('plano'),
                data.get('limite_veiculos'),
                data.get('limite_usuarios'),
                empresa_id
            ))
        
        conn.commit()
        conn.close()
        
        log_action(f'Atualizou empresa ID: {empresa_id}')
        
        return jsonify({
            'success': True,
            'message': 'Empresa atualizada com sucesso!'
        })
        
    except Exception as e:
        print(f"Erro ao atualizar empresa: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# =============================================
# ROTAS - FORNECEDORES
# =============================================

@app.route('/fornecedores')
@login_required
def fornecedores():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fornecedores")
    fornecedores = cursor.fetchall()
    conn.close()
    return render_template('fornecedores.html', fornecedores=fornecedores)

@app.route('/fornecedores/criar', methods=['POST'])
@login_required
def criar_fornecedor():
    """Criar novo fornecedor"""
    try:
        data = request.json
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fornecedores (nome, contato, telefone, email, especialidade)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('nome'),
            data.get('contato'),
            data.get('telefone'),
            data.get('email'),
            data.get('especialidade')
        ))
        
        conn.commit()
        fornecedor_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Fornecedor cadastrado com sucesso!',
            'id': fornecedor_id
        })
        
    except Exception as e:
        print(f"Erro ao criar fornecedor: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao criar fornecedor: {str(e)}'
        }), 500

@app.route('/fornecedores/detalhes/<int:fornecedor_id>', methods=['GET'])
@login_required
def detalhes_fornecedor(fornecedor_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nome, contato, telefone, email, especialidade
            FROM fornecedores 
            WHERE id = ?
        """, (fornecedor_id,))
        
        fornecedor_data = cursor.fetchone()
        conn.close()
        
        if fornecedor_data:
            fornecedor = {
                'id': fornecedor_data[0],
                'nome': fornecedor_data[1],
                'contato': fornecedor_data[2],
                'telefone': fornecedor_data[3],
                'email': fornecedor_data[4],
                'especialidade': fornecedor_data[5],
                'cnpj': 'Não informado',
                'inscricao_estadual': 'Não informado',
                'endereco': 'Não informado',
                'site': 'Não informado',
                'prazo_pagamento': 'Não informado',
                'observacoes': 'Nenhuma observação cadastrada'
            }
            return jsonify(fornecedor)
        else:
            return jsonify({'error': 'Fornecedor não encontrado'}), 404
            
    except Exception as e:
        print(f"Erro ao buscar fornecedor: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/fornecedores/editar/<int:fornecedor_id>', methods=['PUT'])
@login_required
def editar_fornecedor(fornecedor_id):
    try:
        dados = request.get_json()
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE fornecedores 
            SET nome = ?, contato = ?, telefone = ?, email = ?, especialidade = ?
            WHERE id = ?
        """, (
            dados.get('nome'),
            dados.get('contato'),
            dados.get('telefone'),
            dados.get('email'),
            dados.get('especialidade'),
            fornecedor_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Fornecedor atualizado com sucesso'})
        
    except Exception as e:
        print(f"Erro ao editar fornecedor: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/fornecedores/excluir/<int:fornecedor_id>', methods=['DELETE'])
@login_required
def excluir_fornecedor(fornecedor_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verifica se o fornecedor existe
        cursor.execute("SELECT nome FROM fornecedores WHERE id = ?", (fornecedor_id,))
        fornecedor = cursor.fetchone()
        
        if not fornecedor:
            conn.close()
            return jsonify({'success': False, 'error': 'Fornecedor não encontrado'}), 404
        
        # Exclui o fornecedor
        cursor.execute("DELETE FROM fornecedores WHERE id = ?", (fornecedor_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Fornecedor excluído com sucesso'})
        
    except Exception as e:
        print(f"Erro ao excluir fornecedor: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================
# ROTAS DE CLIENTES (MODO SERVICO)
# =============================================

@app.route('/clientes')
@login_required
def clientes():
    """
    Listagem de clientes - APENAS para empresas SERVICO
    """
    from empresa_helpers import is_servico, get_empresa_id
    
    if not is_servico():
        flash('Este recurso está disponível apenas para empresas de Prestação de Serviços.', 'warning')
        return redirect(url_for('dashboard'))
    
    empresa_id = get_empresa_id()
    clientes_lista = []
    novos_mes = 0
    
    try:
        if Config.IS_POSTGRES:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, nome, documento, tipo_documento, telefone, email, 
                       endereco, cidade, estado, cep, observacoes, status, created_at
                FROM clientes 
                WHERE empresa_id = %s
                ORDER BY nome
            """, (empresa_id,))
            clientes_lista = cursor.fetchall()
            
            # Contar novos clientes do mês
            cursor.execute("""
                SELECT COUNT(*) as total FROM clientes 
                WHERE empresa_id = %s 
                AND created_at >= date_trunc('month', CURRENT_DATE)
            """, (empresa_id,))
            novos_mes = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()
        else:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, nome, documento, tipo_documento, telefone, email, 
                       endereco, cidade, estado, cep, observacoes, status, created_at
                FROM clientes 
                WHERE empresa_id = ?
                ORDER BY nome
            """, (empresa_id,))
            clientes_lista = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT COUNT(*) as total FROM clientes 
                WHERE empresa_id = ? 
                AND created_at >= date('now', 'start of month')
            """, (empresa_id,))
            novos_mes = cursor.fetchone()['total']
            
            conn.close()
            
    except Exception as e:
        print(f"Erro ao listar clientes: {e}")
        traceback.print_exc()
        flash('Erro ao carregar lista de clientes.', 'danger')
    
    return render_template('clientes.html', clientes=clientes_lista, novos_mes=novos_mes)


@app.route('/clientes/criar', methods=['POST'])
@login_required
def criar_cliente():
    """Criar novo cliente"""
    from empresa_helpers import is_servico, get_empresa_id
    
    if not is_servico():
        return jsonify({'success': False, 'message': 'Recurso não disponível para sua empresa'}), 403
    
    try:
        data = request.json
        empresa_id = get_empresa_id()
        
        # Validação
        if not data.get('nome') or not data.get('nome').strip():
            return jsonify({'success': False, 'message': 'Nome do cliente é obrigatório'}), 400
        
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO clientes (empresa_id, nome, documento, tipo_documento, telefone, email, 
                                      endereco, cidade, estado, cep, observacoes, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ATIVO')
                RETURNING id
            """, (
                empresa_id,
                data.get('nome', '').strip(),
                data.get('documento', '').strip() or None,
                data.get('tipo_documento', '').strip() or None,
                data.get('telefone', '').strip() or None,
                data.get('email', '').strip() or None,
                data.get('endereco', '').strip() or None,
                data.get('cidade', '').strip() or None,
                data.get('estado', '').strip() or None,
                data.get('cep', '').strip() or None,
                data.get('observacoes', '').strip() or None
            ))
            
            cliente_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
        else:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO clientes (empresa_id, nome, documento, tipo_documento, telefone, email, 
                                      endereco, cidade, estado, cep, observacoes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ATIVO')
            """, (
                empresa_id,
                data.get('nome', '').strip(),
                data.get('documento', '').strip() or None,
                data.get('tipo_documento', '').strip() or None,
                data.get('telefone', '').strip() or None,
                data.get('email', '').strip() or None,
                data.get('endereco', '').strip() or None,
                data.get('cidade', '').strip() or None,
                data.get('estado', '').strip() or None,
                data.get('cep', '').strip() or None,
                data.get('observacoes', '').strip() or None
            ))
            
            cliente_id = cursor.lastrowid
            conn.commit()
            conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Cliente cadastrado com sucesso!',
            'id': cliente_id
        })
        
    except Exception as e:
        print(f"Erro ao criar cliente: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro ao criar cliente: {str(e)}'}), 500


@app.route('/clientes/detalhes/<int:cliente_id>', methods=['GET'])
@login_required
def detalhes_cliente(cliente_id):
    """Obter detalhes de um cliente"""
    from empresa_helpers import is_servico, get_empresa_id
    
    if not is_servico():
        return jsonify({'error': 'Recurso não disponível para sua empresa'}), 403
    
    try:
        empresa_id = get_empresa_id()
        
        if Config.IS_POSTGRES:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, nome, documento, tipo_documento, telefone, email, 
                       endereco, cidade, estado, cep, observacoes, status, created_at
                FROM clientes 
                WHERE id = %s AND empresa_id = %s
            """, (cliente_id, empresa_id))
            cliente = cursor.fetchone()
            
            cursor.close()
            conn.close()
        else:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, nome, documento, tipo_documento, telefone, email, 
                       endereco, cidade, estado, cep, observacoes, status, created_at
                FROM clientes 
                WHERE id = ? AND empresa_id = ?
            """, (cliente_id, empresa_id))
            row = cursor.fetchone()
            cliente = dict(row) if row else None
            
            conn.close()
        
        if not cliente:
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        # Converter datetime para string se necessário
        if cliente.get('created_at'):
            cliente['created_at'] = str(cliente['created_at'])
            
        return jsonify(cliente)
        
    except Exception as e:
        print(f"Erro ao buscar cliente: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/clientes/editar/<int:cliente_id>', methods=['PUT'])
@login_required
def editar_cliente(cliente_id):
    """Editar cliente existente"""
    from empresa_helpers import is_servico, get_empresa_id
    
    if not is_servico():
        return jsonify({'success': False, 'message': 'Recurso não disponível para sua empresa'}), 403
    
    try:
        data = request.json
        empresa_id = get_empresa_id()
        
        # Validação
        if not data.get('nome') or not data.get('nome').strip():
            return jsonify({'success': False, 'message': 'Nome do cliente é obrigatório'}), 400
        
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            # Verificar se pertence à empresa
            cursor.execute("SELECT id FROM clientes WHERE id = %s AND empresa_id = %s", (cliente_id, empresa_id))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Cliente não encontrado'}), 404
            
            cursor.execute("""
                UPDATE clientes SET
                    nome = %s,
                    documento = %s,
                    tipo_documento = %s,
                    telefone = %s,
                    email = %s,
                    endereco = %s,
                    cidade = %s,
                    estado = %s,
                    cep = %s,
                    observacoes = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND empresa_id = %s
            """, (
                data.get('nome', '').strip(),
                data.get('documento', '').strip() or None,
                data.get('tipo_documento', '').strip() or None,
                data.get('telefone', '').strip() or None,
                data.get('email', '').strip() or None,
                data.get('endereco', '').strip() or None,
                data.get('cidade', '').strip() or None,
                data.get('estado', '').strip() or None,
                data.get('cep', '').strip() or None,
                data.get('observacoes', '').strip() or None,
                cliente_id,
                empresa_id
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        else:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            # Verificar se pertence à empresa
            cursor.execute("SELECT id FROM clientes WHERE id = ? AND empresa_id = ?", (cliente_id, empresa_id))
            if not cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': 'Cliente não encontrado'}), 404
            
            cursor.execute("""
                UPDATE clientes SET
                    nome = ?,
                    documento = ?,
                    tipo_documento = ?,
                    telefone = ?,
                    email = ?,
                    endereco = ?,
                    cidade = ?,
                    estado = ?,
                    cep = ?,
                    observacoes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND empresa_id = ?
            """, (
                data.get('nome', '').strip(),
                data.get('documento', '').strip() or None,
                data.get('tipo_documento', '').strip() or None,
                data.get('telefone', '').strip() or None,
                data.get('email', '').strip() or None,
                data.get('endereco', '').strip() or None,
                data.get('cidade', '').strip() or None,
                data.get('estado', '').strip() or None,
                data.get('cep', '').strip() or None,
                data.get('observacoes', '').strip() or None,
                cliente_id,
                empresa_id
            ))
            
            conn.commit()
            conn.close()
        
        return jsonify({'success': True, 'message': 'Cliente atualizado com sucesso!'})
        
    except Exception as e:
        print(f"Erro ao editar cliente: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro ao editar cliente: {str(e)}'}), 500


@app.route('/clientes/toggle-status/<int:cliente_id>', methods=['PUT'])
@login_required
def toggle_status_cliente(cliente_id):
    """Ativar/Inativar cliente"""
    from empresa_helpers import is_servico, get_empresa_id
    
    if not is_servico():
        return jsonify({'success': False, 'message': 'Recurso não disponível para sua empresa'}), 403
    
    try:
        data = request.json
        empresa_id = get_empresa_id()
        novo_status = data.get('status', 'INATIVO')
        
        if novo_status not in ['ATIVO', 'INATIVO']:
            return jsonify({'success': False, 'message': 'Status inválido'}), 400
        
        if Config.IS_POSTGRES:
            import psycopg2
            conn = psycopg2.connect(Config.DATABASE_URL)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE clientes SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND empresa_id = %s
            """, (novo_status, cliente_id, empresa_id))
            
            if cursor.rowcount == 0:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Cliente não encontrado'}), 404
            
            conn.commit()
            cursor.close()
            conn.close()
        else:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE clientes SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND empresa_id = ?
            """, (novo_status, cliente_id, empresa_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'success': False, 'message': 'Cliente não encontrado'}), 404
            
            conn.commit()
            conn.close()
        
        acao = 'ativado' if novo_status == 'ATIVO' else 'inativado'
        return jsonify({'success': True, 'message': f'Cliente {acao} com sucesso!'})
        
    except Exception as e:
        print(f"Erro ao alterar status do cliente: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


# =============================================
# ROTAS DE TÉCNICOS
# =============================================

@app.route('/tecnicos')
@login_required
def tecnicos():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tecnicos ORDER BY nome")
    tecnicos = cursor.fetchall()
    conn.close()
    return render_template('tecnicos.html', tecnicos=tecnicos)

@app.route('/api/tecnico/<int:tecnico_id>', methods=['GET'])
@login_required
def buscar_tecnico(tecnico_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tecnicos WHERE id=?", (tecnico_id,))
        tecnico = cursor.fetchone()
        conn.close()
        
        if tecnico:
            return jsonify({
                'id': tecnico[0],
                'nome': tecnico[1],
                'cpf': tecnico[2],
                'telefone': tecnico[3],
                'email': tecnico[4],
                'especialidade': tecnico[5],
                'data_admissao': tecnico[6],
                'status': tecnico[7]
            })
        else:
            return jsonify({'success': False, 'message': 'Técnico não encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/tecnico/<int:tecnico_id>/historico', methods=['GET'])
@login_required
def historico_tecnico(tecnico_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Busca manutenções realizadas pelo técnico
        cursor.execute("""
            SELECT COALESCE(m.data_realizada, m.data_agendada) as data, 
                   v.placa, v.modelo, m.tipo, m.status
            FROM manutencoes m
            LEFT JOIN veiculos v ON m.veiculo_id = v.id
            WHERE m.tecnico = (SELECT nome FROM tecnicos WHERE id = ?)
            ORDER BY data DESC
            LIMIT 10
        """, (tecnico_id,))
        
        manutencoes = cursor.fetchall()
        conn.close()
        
        historico = []
        for m in manutencoes:
            historico.append({
                'data': m[0] if m[0] else 'Não informado',
                'veiculo': f"{m[1]} - {m[2]}" if m[1] else 'Não informado',
                'tipo': m[3],
                'status': m[4]
            })
        
        return jsonify(historico)
        
    except Exception as e:
        print(f"Erro ao buscar histórico: {e}")
        traceback.print_exc()
        return jsonify([]), 500

@app.route('/api/manutencoes/calendario', methods=['GET'])
@login_required
def get_manutencoes_calendario():
    """Retorna manutenções formatadas para o FullCalendar"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Buscar todas as manutenções com informações do veículo
        cursor.execute('''
            SELECT 
                m.id,
                m.tipo,
                m.status,
                m.data_agendada,
                m.data_realizada,
                v.placa,
                v.modelo
            FROM manutencoes m
            LEFT JOIN veiculos v ON m.veiculo_id = v.id
            ORDER BY m.data_agendada DESC
        ''')
        
        manutencoes = cursor.fetchall()
        conn.close()
        
        # Mapear cores por status
        cores = {
            'Agendada': '#0d6efd',      # Azul (Bootstrap primary)
            'Em Andamento': '#ffc107',  # Amarelo (Bootstrap warning)
            'Concluída': '#198754',     # Verde (Bootstrap success)
            'Cancelada': '#dc3545'      # Vermelho (Bootstrap danger)
        }
        
        # Formatar eventos para o FullCalendar
        eventos = []
        for m in manutencoes:
            # Usar data_realizada se existir, senão data_agendada
            data = m[4] if m[4] else m[3]
            
            if data:  # Apenas se houver data
                eventos.append({
                    'id': m[0],
                    'title': f"{m[5]} - {m[1]}",  # Placa - Tipo
                    'start': data,
                    'backgroundColor': cores.get(m[2], '#6c757d'),
                    'borderColor': cores.get(m[2], '#6c757d'),
                    'extendedProps': {
                        'veiculo': f"{m[5]} - {m[6]}",  # Placa - Modelo
                        'tipo': m[1],
                        'status': m[2]
                    }
                })
        
        return jsonify(eventos)
        
    except Exception as e:
        print(f"Erro ao buscar manutenções para calendário: {e}")
        traceback.print_exc()
        return jsonify([]), 500

@app.route('/api/tecnico', methods=['POST'])
@login_required
def criar_tecnico():
    conn = None
    try:
        print("DEBUG: Recebendo requisição POST /api/tecnico")
        print("DEBUG: Headers:", dict(request.headers))
        print("DEBUG: JSON data:", request.json)
        
        data = request.json
        conn = sqlite3.connect(DATABASE, timeout=30.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tecnicos (nome, cpf, telefone, email, especialidade, data_admissao, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['nome'],
            data.get('cpf', ''),
            data.get('telefone', ''),
            data.get('email', ''),
            data.get('especialidade', ''),
            data.get('data_admissao', ''),
            data.get('status', 'Ativo')
        ))
        
        conn.commit()
        tecnico_id = cursor.lastrowid
        
        print(f"DEBUG: Técnico criado com ID {tecnico_id}")
        return jsonify({'success': True, 'id': tecnico_id, 'message': 'Técnico cadastrado com sucesso!'})
    except Exception as e:
        print(f"DEBUG ERRO: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        if conn:
            conn.close()

@app.route('/api/tecnico/<int:tecnico_id>', methods=['PUT'])
@login_required
def editar_tecnico(tecnico_id):
    try:
        data = request.json
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tecnicos 
            SET nome=?, cpf=?, telefone=?, email=?, especialidade=?, data_admissao=?, status=?
            WHERE id=?
        ''', (
            data['nome'],
            data.get('cpf', ''),
            data.get('telefone', ''),
            data.get('email', ''),
            data.get('especialidade', ''),
            data.get('data_admissao', ''),
            data.get('status', 'Ativo'),
            tecnico_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Técnico atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/tecnico/<int:tecnico_id>', methods=['DELETE'])
@login_required
def excluir_tecnico(tecnico_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tecnicos WHERE id=?', (tecnico_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Técnico excluído com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/relatorios')
@login_required
def relatorios():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Obter filtros da query string
    data_inicial = request.args.get('data_inicial', '')
    data_final = request.args.get('data_final', '')
    veiculo_id = request.args.get('veiculo_id', '')
    
    # Construir condições WHERE
    where_conditions = ["data_realizada IS NOT NULL"]
    params = []
    
    if data_inicial:
        where_conditions.append("data_realizada >= ?")
        params.append(data_inicial)
    
    if data_final:
        where_conditions.append("data_realizada <= ?")
        params.append(data_final)
    
    if veiculo_id:
        where_conditions.append("veiculo_id = ?")
        params.append(veiculo_id)
    
    where_clause = " AND ".join(where_conditions)
    
    # Custo total de manutenção por mês (com filtros)
    cursor.execute(f'''
        SELECT strftime('%Y-%m', data_realizada) as mes, SUM(custo) as total
        FROM manutencoes 
        WHERE {where_clause}
        GROUP BY mes 
        ORDER BY mes DESC 
        LIMIT 12
    ''', params)
    custos_mensais = cursor.fetchall()
    print(f"DEBUG - Custos mensais: {custos_mensais}")
    
    # Converter custos mensais para formato JSON adequado
    custos_mensais_json = [[row[0], row[1]] for row in custos_mensais]
    
    # Veículos com mais manutenções (com filtros de data)
    where_veiculos = []
    params_veiculos = []
    if data_inicial:
        where_veiculos.append("m.data_realizada >= ?")
        params_veiculos.append(data_inicial)
    if data_final:
        where_veiculos.append("m.data_realizada <= ?")
        params_veiculos.append(data_final)
    if veiculo_id:
        where_veiculos.append("v.id = ?")
        params_veiculos.append(veiculo_id)
    
    where_veiculos_clause = " AND ".join(where_veiculos) if where_veiculos else "1=1"
    
    cursor.execute(f'''
        SELECT v.placa, v.modelo, COUNT(m.id) as total_manutencoes
        FROM veiculos v 
        LEFT JOIN manutencoes m ON v.id = m.veiculo_id AND {where_veiculos_clause}
        GROUP BY v.id 
        ORDER BY total_manutencoes DESC 
        LIMIT 10
    ''', params_veiculos)
    veiculos_mais_manutencoes = cursor.fetchall()
    
    # Tipos de manutenção (dados reais com filtros)
    cursor.execute(f'''
        SELECT tipo, COUNT(*) as quantidade
        FROM manutencoes
        WHERE {where_clause}
        GROUP BY tipo
        ORDER BY quantidade DESC
    ''', params)
    tipos_manutencao = cursor.fetchall()
    print(f"DEBUG - Tipos manutenção: {tipos_manutencao}")
    
    # Converter tipos de manutenção para formato JSON adequado
    tipos_manutencao_json = [[row[0], row[1]] for row in tipos_manutencao]
    
    # Estatísticas para os cards (com filtros)
    # Custo total
    if data_inicial or data_final or veiculo_id:
        where_stats = []
        params_stats = []
        if data_inicial:
            where_stats.append("data_realizada >= ?")
            params_stats.append(data_inicial)
        if data_final:
            where_stats.append("data_realizada <= ?")
            params_stats.append(data_final)
        if veiculo_id:
            where_stats.append("veiculo_id = ?")
            params_stats.append(veiculo_id)
        where_stats_clause = " AND ".join(where_stats)
        
        cursor.execute(f'''
            SELECT COALESCE(SUM(custo), 0) as total
            FROM manutencoes
            WHERE {where_stats_clause}
        ''', params_stats)
    else:
        cursor.execute('''
            SELECT COALESCE(SUM(custo), 0) as total
            FROM manutencoes
                WHERE data_realizada >= date('now', '-12 months')
        ''')
    custo_total_ano = cursor.fetchone()[0]
    
    # Média mensal (com filtros)
    if data_inicial or data_final or veiculo_id:
        cursor.execute(f'''
            SELECT COALESCE(AVG(custo_mensal), 0) as media
            FROM (
                SELECT SUM(custo) as custo_mensal
                FROM manutencoes
                WHERE {where_stats_clause}
                GROUP BY strftime('%Y-%m', data_realizada)
            )
        ''', params_stats)
    else:
        cursor.execute('''
            SELECT COALESCE(AVG(custo_mensal), 0) as media
            FROM (
                SELECT SUM(custo) as custo_mensal
                FROM manutencoes
                WHERE data_realizada >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', data_realizada)
            )
        ''')
    media_mensal = cursor.fetchone()[0]
    
    # Total de manutenções realizadas (com filtros)
    if data_inicial or data_final or veiculo_id:
        cursor.execute(f'''
            SELECT COUNT(*) as total
            FROM manutencoes
            WHERE status = 'Concluída' AND {where_stats_clause}
        ''', params_stats)
    else:
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM manutencoes
            WHERE status = 'Concluída'
        ''')
    total_manutencoes = cursor.fetchone()[0]
    
    # Manutenções emergenciais (com filtros)
    if data_inicial or data_final or veiculo_id:
        cursor.execute(f'''
            SELECT COUNT(*) as total
            FROM manutencoes
            WHERE tipo = 'Emergencial' AND status = 'Concluída' AND {where_stats_clause}
        ''', params_stats)
    else:
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM manutencoes
            WHERE tipo = 'Emergencial' AND status = 'Concluída'
        ''')
    manutencoes_emergenciais = cursor.fetchone()[0]
    
    # Buscar todos os veículos para o dropdown
    cursor.execute('SELECT id, placa, modelo FROM veiculos ORDER BY placa')
    veiculos = cursor.fetchall()
    
    conn.close()
    return render_template('relatorios.html', 
                         custos_mensais=custos_mensais_json,
                         veiculos_mais_manutencoes=veiculos_mais_manutencoes,
                         tipos_manutencao=tipos_manutencao_json,
                         custo_total_ano=custo_total_ano,
                         media_mensal=media_mensal,
                         total_manutencoes=total_manutencoes,
                         manutencoes_emergenciais=manutencoes_emergenciais,
                         veiculos=veiculos,
                         data_inicial=data_inicial,
                         data_final=data_final,
                         veiculo_id=veiculo_id)

# =============================================
# ROTAS DE EXPORTAÇÃO DE RELATÓRIOS
# =============================================

@app.route('/exportar/excel')
@login_required
def exportar_excel():
    """Exporta relatório completo em formato CSV (compatível com Excel)"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Obter filtros
        data_inicial = request.args.get('data_inicial', '')
        data_final = request.args.get('data_final', '')
        veiculo_id = request.args.get('veiculo_id', '')
        
        # Construir WHERE clause
        where_conditions = ["m.data_realizada IS NOT NULL"]
        params = []
        
        if data_inicial:
            where_conditions.append("m.data_realizada >= ?")
            params.append(data_inicial)
        
        if data_final:
            where_conditions.append("m.data_realizada <= ?")
            params.append(data_final)
        
        if veiculo_id:
            where_conditions.append("m.veiculo_id = ?")
            params.append(veiculo_id)
        
        where_clause = " AND ".join(where_conditions)
        
        # Buscar todas as manutenções
        cursor.execute(f'''
            SELECT 
                m.id,
                v.placa,
                v.modelo,
                m.tipo,
                m.descricao,
                m.data_realizada,
                m.custo,
                m.status,
                m.tecnico
            FROM manutencoes m
            LEFT JOIN veiculos v ON m.veiculo_id = v.id
            WHERE {where_clause}
            ORDER BY m.data_realizada DESC
        ''', params)
        
        manutencoes = cursor.fetchall()
        conn.close()
        
        # Criar CSV com UTF-8 BOM para Excel
        output = BytesIO()
        # Adicionar BOM UTF-8 para que Excel reconheça a codificação
        output.write('\ufeff'.encode('utf-8'))
        
        # Escrever CSV
        wrapper = codecs.getwriter('utf-8')(output)
        writer = csv.writer(wrapper, delimiter=';', lineterminator='\n')
        
        # Cabeçalho
        writer.writerow(['ID', 'Placa', 'Modelo', 'Tipo', 'Descricao', 'Data', 'Custo (R$)', 'Status', 'Tecnico'])
        
        # Dados
        for m in manutencoes:
            writer.writerow([
                m[0],  # ID
                m[1] if m[1] else '',  # Placa
                m[2] if m[2] else '',  # Modelo
                m[3] if m[3] else '',  # Tipo
                m[4] if m[4] else '',  # Descrição
                m[5] if m[5] else '',  # Data
                f"{m[6]:.2f}".replace('.', ',') if m[6] else '0,00',  # Custo
                m[7] if m[7] else '',  # Status
                m[8] if m[8] else 'N/A'  # Técnico
            ])
        
        # Preparar resposta
        output.seek(0)
        
        filename = f"relatorio_manutencoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        print(f"Erro na exportação Excel: {str(e)}")  # Debug
        import traceback
        traceback.print_exc()  # Mostra stack trace completo
        return jsonify({'error': str(e)}), 500

@app.route('/exportar/pdf-completo')
@login_required
def exportar_pdf_completo():
    """Exporta relatório COMPLETO com todas as manutenções em PDF"""
    try:
        from io import BytesIO
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Obter filtros
        data_inicial = request.args.get('data_inicial', '')
        data_final = request.args.get('data_final', '')
        veiculo_id = request.args.get('veiculo_id', '')
        
        # Construir WHERE clause
        where_conditions = ["m.data_realizada IS NOT NULL"]
        params = []
        
        if data_inicial:
            where_conditions.append("m.data_realizada >= ?")
            params.append(data_inicial)
        
        if data_final:
            where_conditions.append("m.data_realizada <= ?")
            params.append(data_final)
        
        if veiculo_id:
            where_conditions.append("m.veiculo_id = ?")
            params.append(veiculo_id)
        
        where_clause = " AND ".join(where_conditions)
        
        # Buscar TODAS as manutenções
        cursor.execute(f'''
            SELECT 
                m.id,
                v.placa,
                v.modelo,
                m.tipo,
                m.descricao,
                m.data_realizada,
                m.custo,
                m.status,
                m.tecnico
            FROM manutencoes m
            LEFT JOIN veiculos v ON m.veiculo_id = v.id
            WHERE {where_clause}
            ORDER BY m.data_realizada DESC
        ''', params)
        
        manutencoes = cursor.fetchall()
        
        # Buscar estatísticas
        cursor.execute(f'''
            SELECT 
                COALESCE(SUM(custo), 0) as total,
                COALESCE(AVG(custo), 0) as media,
                COUNT(*) as quantidade
            FROM manutencoes m
            WHERE {where_clause}
        ''', params)
        stats = cursor.fetchone()
        
        conn.close()
        
        # Criar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#0066cc'),
            spaceAfter=20,
            alignment=1  # Center
        )
        elements.append(Paragraph('RELATÓRIO COMPLETO DE MANUTENÇÕES', title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Período e filtros
        periodo_texto = "Período: "
        if data_inicial and data_final:
            periodo_texto += f"{data_inicial} até {data_final}"
        elif data_inicial:
            periodo_texto += f"A partir de {data_inicial}"
        elif data_final:
            periodo_texto += f"Até {data_final}"
        else:
            periodo_texto += "Todos os registros"
        
        if veiculo_id:
            # Buscar info do veículo
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('SELECT placa, modelo FROM veiculos WHERE id = ?', (veiculo_id,))
            veiculo_info = cursor.fetchone()
            conn.close()
            if veiculo_info:
                periodo_texto += f" | Veículo: {veiculo_info[0]} - {veiculo_info[1]}"
        
        elements.append(Paragraph(periodo_texto, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Resumo Financeiro
        resumo_style = ParagraphStyle(
            'Resumo',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#28a745'),
            spaceAfter=5
        )
        
        total_formatado = f'R$ {stats[0]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        media_formatada = f'R$ {stats[1]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        elements.append(Paragraph(f'<b>Total Gasto:</b> {total_formatado} | <b>Média:</b> {media_formatada} | <b>Quantidade:</b> {stats[2]}', resumo_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Tabela de Manutenções
        data_table = [['ID', 'Placa', 'Modelo', 'Tipo', 'Descrição', 'Data', 'Custo', 'Status']]
        
        for m in manutencoes:
            custo_formatado = f'R$ {m[6]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') if m[6] else 'R$ 0,00'
            descricao = m[4][:30] + '...' if m[4] and len(m[4]) > 30 else (m[4] if m[4] else '-')
            
            data_table.append([
                str(m[0]),
                m[1] if m[1] else '-',
                m[2] if m[2] else '-',
                m[3] if m[3] else '-',
                descricao,
                m[5] if m[5] else '-',
                custo_formatado,
                m[7] if m[7] else '-'
            ])
        
        # Criar tabela com larguras ajustadas
        col_widths = [0.4*inch, 0.9*inch, 1.2*inch, 0.9*inch, 1.8*inch, 0.9*inch, 0.9*inch, 0.9*inch]
        table = Table(data_table, colWidths=col_widths, repeatRows=1)
        
        table.setStyle(TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Corpo
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # ID
            ('ALIGN', (6, 1), (6, -1), 'RIGHT'),   # Custo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Rodapé
        elements.append(Paragraph(
            f'Relatório completo gerado em: {datetime.now().strftime("%d/%m/%Y às %H:%M")} | Total de manutenções: {len(manutencoes)}',
            styles['Italic']
        ))
        
        # Construir PDF
        doc.build(elements)
        buffer.seek(0)
        
        filename = f"relatorio_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Erro na exportação PDF completo: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/exportar/pdf')
@login_required
def exportar_pdf():
    """Exporta resumo executivo em PDF"""
    try:
        from io import BytesIO
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Obter filtros
        data_inicial = request.args.get('data_inicial', '')
        data_final = request.args.get('data_final', '')
        veiculo_id = request.args.get('veiculo_id', '')
        
        # Construir WHERE clause
        where_conditions = []
        params = []
        
        if data_inicial:
            where_conditions.append("data_realizada >= ?")
            params.append(data_inicial)
        
        if data_final:
            where_conditions.append("data_realizada <= ?")
            params.append(data_final)
        
        if veiculo_id:
            where_conditions.append("veiculo_id = ?")
            params.append(veiculo_id)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Estatísticas
        cursor.execute(f'''
            SELECT 
                COALESCE(SUM(custo), 0) as total,
                COALESCE(AVG(custo), 0) as media,
                COUNT(*) as quantidade
            FROM manutencoes
            WHERE {where_clause}
        ''', params)
        stats = cursor.fetchone()
        
        # Top 5 veículos
        cursor.execute(f'''
            SELECT v.placa, v.modelo, COUNT(m.id) as total, COALESCE(SUM(m.custo), 0) as custo_total
            FROM veiculos v
            LEFT JOIN manutencoes m ON v.id = m.veiculo_id AND {where_clause}
            GROUP BY v.id
            ORDER BY total DESC
            LIMIT 5
        ''', params)
        top_veiculos = cursor.fetchall()
        
        conn.close()
        
        # Criar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0066cc'),
            spaceAfter=30,
            alignment=1  # Center
        )
        elements.append(Paragraph('RESUMO EXECUTIVO - MANUTENÇÕES', title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Período
        periodo_texto = "Período: "
        if data_inicial and data_final:
            periodo_texto += f"{data_inicial} até {data_final}"
        elif data_inicial:
            periodo_texto += f"A partir de {data_inicial}"
        elif data_final:
            periodo_texto += f"Até {data_final}"
        else:
            periodo_texto += "Todos os registros"
        
        elements.append(Paragraph(periodo_texto, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Estatísticas
        data_stats = [
            ['ESTATÍSTICAS GERAIS', ''],
            ['Total Gasto', f'R$ {stats[0]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Custo Médio', f'R$ {stats[1]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Quantidade de Manutenções', str(stats[2])]
        ]
        
        table_stats = Table(data_stats, colWidths=[3*inch, 2*inch])
        table_stats.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table_stats)
        elements.append(Spacer(1, 0.5*inch))
        
        # Top 5 veículos
        elements.append(Paragraph('TOP 5 VEÍCULOS COM MAIS MANUTENÇÕES', styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        data_veiculos = [['Placa', 'Modelo', 'Manutenções', 'Custo Total']]
        for v in top_veiculos:
            custo_formatado = f'R$ {v[3]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
            data_veiculos.append([v[0], v[1], str(v[2]), custo_formatado])
        
        table_veiculos = Table(data_veiculos, colWidths=[1.5*inch, 2*inch, 1.2*inch, 1.5*inch])
        table_veiculos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table_veiculos)
        elements.append(Spacer(1, 0.5*inch))
        
        # Rodapé
        elements.append(Paragraph(
            f'Relatório gerado em: {datetime.now().strftime("%d/%m/%Y às %H:%M")}',
            styles['Italic']
        ))
        
        # Construir PDF
        doc.build(elements)
        buffer.seek(0)
        
        filename = f"resumo_executivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/exportar/csv')
@login_required
def exportar_csv():
    """Exporta dados brutos em CSV"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Obter filtros
        data_inicial = request.args.get('data_inicial', '')
        data_final = request.args.get('data_final', '')
        veiculo_id = request.args.get('veiculo_id', '')
        
        # Construir WHERE clause
        where_conditions = []
        params = []
        
        if data_inicial:
            where_conditions.append("m.data_realizada >= ?")
            params.append(data_inicial)
        
        if data_final:
            where_conditions.append("m.data_realizada <= ?")
            params.append(data_final)
        
        if veiculo_id:
            where_conditions.append("m.veiculo_id = ?")
            params.append(veiculo_id)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Buscar dados brutos
        cursor.execute(f'''
            SELECT 
                m.id,
                m.data_realizada,
                v.placa,
                v.modelo,
                v.tipo as tipo_veiculo,
                m.tipo as tipo_manutencao,
                m.custo,
                m.status
            FROM manutencoes m
            LEFT JOIN veiculos v ON m.veiculo_id = v.id
            WHERE {where_clause}
            ORDER BY m.data_realizada DESC
        ''', params)
        
        dados = cursor.fetchall()
        conn.close()
        
        # Criar CSV com UTF-8 BOM
        output = BytesIO()
        # Adicionar BOM UTF-8
        output.write('\ufeff'.encode('utf-8'))
        
        # Escrever CSV
        wrapper = codecs.getwriter('utf-8')(output)
        writer = csv.writer(wrapper, lineterminator='\n')
        
        # Cabeçalho
        writer.writerow(['id', 'data', 'placa', 'modelo', 'tipo_veiculo', 'tipo_manutencao', 'custo', 'status'])
        
        # Dados - tratar None values
        for d in dados:
            row = []
            for value in d:
                if value is None:
                    row.append('')
                else:
                    row.append(str(value))
            writer.writerow(row)
        
        # Preparar resposta
        output.seek(0)
        
        filename = f"dados_brutos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        print(f"Erro na exportação CSV: {str(e)}")  # Debug
        import traceback
        traceback.print_exc()  # Mostra stack trace completo
        return jsonify({'error': str(e)}), 500

def gerar_catalogo_pdf():
    """Gera um PDF detalhado com todas as peças do catálogo"""
    # Buscar todas as peças do banco
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.nome, p.codigo, p.veiculo_compativel, p.preco, p.quantidade_estoque, f.nome as fornecedor
        FROM pecas p 
        LEFT JOIN fornecedores f ON p.fornecedor_id = f.id 
        ORDER BY p.nome
    ''')
    pecas = cursor.fetchall()
    conn.close()
    
    # Criar diretório para PDFs se não existir
    pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'pdfs')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Caminho do arquivo PDF
    pdf_path = os.path.join(pdf_dir, 'catalogo_pecas_detalhado.pdf')
    
    # Criar o documento PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Centralizado
    )
    
    # Título
    title = Paragraph("CATÁLOGO DETALHADO DE PEÇAS", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Data de geração
    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
    data_para = Paragraph(f"<b>Gerado em:</b> {data_atual}", styles['Normal'])
    elements.append(data_para)
    elements.append(Spacer(1, 20))
    
    # Criar tabela com dados das peças
    data = [['#', 'Nome da Peça', 'Código', 'Veículo Compatível', 'Preço (R$)', 'Estoque', 'Fornecedor']]
    
    for i, (nome, codigo, veiculo, preco, estoque, fornecedor) in enumerate(pecas, 1):
        data.append([
            str(i),
            nome,
            codigo or 'N/A',
            veiculo or 'Universal',
            f'{preco:.2f}' if preco else '0.00',
            str(estoque) if estoque else '0',
            fornecedor or 'Não informado'
        ])
    
    # Criar e estilizar a tabela
    table = Table(data, colWidths=[0.5*inch, 1.8*inch, 1*inch, 1.5*inch, 0.8*inch, 0.6*inch, 1.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Resumo estatístico
    total_pecas = len(pecas)
    valor_total = sum(preco * estoque for _, _, _, preco, estoque, _ in pecas if preco and estoque)
    estoque_total = sum(estoque for _, _, _, _, estoque, _ in pecas if estoque)
    
    resumo = f"""
    <b>RESUMO ESTATÍSTICO:</b><br/>
    • Total de peças catalogadas: {total_pecas}<br/>
    • Total de unidades em estoque: {estoque_total}<br/>
    • Valor total do estoque: R$ {valor_total:,.2f}<br/>
    • Média de preço por peça: R$ {(sum(preco for _, _, _, preco, _, _ in pecas if preco) / total_pecas):,.2f}
    """
    
    resumo_para = Paragraph(resumo, styles['Normal'])
    elements.append(resumo_para)
    
    # Gerar o PDF
    doc.build(elements)
    return pdf_path

# Rota para servir catálogos PDF
@app.route('/catalogo-pdf')
@login_required
def catalogo_pdf():
    try:
        # Gerar PDF atualizado
        pdf_path = gerar_catalogo_pdf()
        return send_file(pdf_path, as_attachment=False, download_name='catalogo_pecas_detalhado.pdf')
    except Exception as e:
        return f"Erro ao gerar PDF: {str(e)}", 500

# Rota para página de acesso ao catálogo
@app.route('/catalogo')
@login_required
def catalogo_acesso():
    return '''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Catálogo de Peças - Sistema de Manutenção</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .container { margin-top: 50px; }
            .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
            .btn-pdf { background: linear-gradient(45deg, #FF6B6B, #4ECDC4); border: none; padding: 15px 30px; font-size: 18px; border-radius: 10px; }
            .btn-pdf:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.3); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-body text-center p-5">
                            <h1 class="card-title mb-4">
                                <i class="fas fa-file-pdf text-danger me-2"></i>
                                Catálogo de Peças
                            </h1>
                            <p class="lead mb-4">Acesse o catálogo completo com todas as peças, preços e especificações técnicas.</p>
                            
                            <div class="row text-start mb-4">
                                <div class="col-md-6">
                                    <h5><i class="fas fa-check-circle text-success me-2"></i>Inclui:</h5>
                                    <ul class="list-unstyled">
                                        <li><i class="fas fa-cog me-2"></i>Todas as peças em estoque</li>
                                        <li><i class="fas fa-tag me-2"></i>Preços atualizados</li>
                                        <li><i class="fas fa-warehouse me-2"></i>Quantidades disponíveis</li>
                                    </ul>
                                </div>
                                <div class="col-md-6">
                                    <h5><i class="fas fa-star text-warning me-2"></i>Recursos:</h5>
                                    <ul class="list-unstyled">
                                        <li><i class="fas fa-print me-2"></i>Layout para impressão</li>
                                        <li><i class="fas fa-sync me-2"></i>Atualizado em tempo real</li>
                                        <li><i class="fas fa-table me-2"></i>Tabela organizada</li>
                                    </ul>
                                </div>
                            </div>
                            
                            <a href="/catalogo-pdf" class="btn btn-pdf text-white btn-lg">
                                <i class="fas fa-download me-2"></i>
                                Abrir Catálogo PDF
                            </a>
                            
                            <hr class="my-4">
                            <a href="/" class="btn btn-outline-primary">
                                <i class="fas fa-arrow-left me-2"></i>
                                Voltar ao Sistema
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

# Integração com Chatbot
@app.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot():
    mensagem = request.json.get('mensagem', '').lower().strip()
    
    # Reconhecer números das opções do menu e atalhos
    if mensagem == '1' or 'próxima' in mensagem or 'agendada' in mensagem or 'manutenção' in mensagem:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.placa, m.tipo, m.data_agendada 
            FROM manutencoes m 
            JOIN veiculos v ON m.veiculo_id = v.id 
            WHERE m.status = 'Agendada' 
            ORDER BY m.data_agendada 
            LIMIT 3
        ''')
        proximas = cursor.fetchall()
        conn.close()
        
        resposta = "📅 PRÓXIMAS MANUTENÇÕES\n"
        resposta += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, (placa, tipo, data) in enumerate(proximas, 1):
            resposta += f"{i}. {placa} - {tipo}\n"
            resposta += f"   Data: {data}\n\n"
        
        return jsonify({'resposta': resposta})
    
    elif mensagem == '4' or 'estoque' in mensagem or 'baixo' in mensagem:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT nome, quantidade_estoque FROM pecas WHERE quantidade_estoque < 10")
        alertas = cursor.fetchall()
        conn.close()
        
        resposta = "⚠️ ESTOQUE BAIXO\n"
        resposta += "━━━━━━━━━━━━━━━━━\n\n"
        for i, (nome, quantidade) in enumerate(alertas, 1):
            resposta += f"{i}. {nome} - {quantidade} unidades\n"
        
        return jsonify({'resposta': resposta})
    
    elif mensagem == '2' or ('catálogo' in mensagem and 'pdf' not in mensagem) or ('catalogo' in mensagem and 'pdf' not in mensagem) or ('peças' in mensagem and 'pdf' not in mensagem) or ('pecas' in mensagem and 'pdf' not in mensagem):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pecas")
        total_pecas = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(quantidade_estoque) FROM pecas")
        total_estoque = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(preco * quantidade_estoque) FROM pecas WHERE preco IS NOT NULL AND quantidade_estoque IS NOT NULL")
        valor_total = cursor.fetchone()[0] or 0
        conn.close()
        
        resposta = "� RESUMO DO ESTOQUE\n"
        resposta += "━━━━━━━━━━━━━━━━━━━━\n\n"
        resposta += f"🔢 Total de peças: {total_pecas}\n"
        resposta += f"📦 Unidades em estoque: {total_estoque:,}\n"
        resposta += f"💰 Valor total: R$ {valor_total:,.2f}\n\n"
        resposta += "Para ver lista completa digite: 3"
        
        return jsonify({'resposta': resposta})
    
    elif mensagem == '3' or 'pdf' in mensagem:
        resposta = "� CATÁLOGO PDF\n"
        resposta += "━━━━━━━━━━━━━━━━\n\n"
        resposta += "Clique no botão abaixo:\n\n"
        
        resposta += '<a href="http://127.0.0.1:5000/catalogo" target="_blank" style="background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 16px; display: inline-block; margin: 10px 0; box-shadow: 0 4px 15px rgba(0,123,255,0.3); transition: all 0.3s ease;">📄 ABRIR CATÁLOGO</a>\n\n'
        
        resposta += "Lista completa com todas as peças,\npreços e quantidades em estoque."
        
        return jsonify({'resposta': resposta})
    
    elif mensagem == '5' or 'fornecedor' in mensagem or 'contato' in mensagem:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT nome, telefone, especialidade FROM fornecedores LIMIT 3")
        fornecedores = cursor.fetchall()
        conn.close()
        
        resposta = "📞 FORNECEDORES\n"
        resposta += "━━━━━━━━━━━━━━━━\n\n"
        for i, (nome, telefone, especialidade) in enumerate(fornecedores, 1):
            resposta += f"{i}. {nome}\n"
            resposta += f"   {especialidade}\n"
            resposta += f"   📱 {telefone}\n\n"
        
        return jsonify({'resposta': resposta})
    
    else:
        resposta = "🤖 ASSISTENTE DE MANUTENÇÃO\n"
        resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        resposta += "Digite o número da opção:\n\n"
        
        resposta += "1 📅 Ver próximas manutenções\n"
        resposta += "2 � Resumo das peças\n"
        resposta += "3 � Catálogo PDF completo\n"
        resposta += "4 ⚠️  Ver estoque baixo\n"
        resposta += "5 📞 Contatos fornecedores\n\n"
        
        resposta += "Exemplo: Digite apenas \"1\" ou \"2\"\n\n"
        resposta += "❓ O que você precisa?"
        
        return jsonify({'resposta': resposta})

# =============================================
# ROTAS DO MÓDULO FINANCEIRO
# =============================================

@app.route('/financeiro')
@login_required
def financeiro():
    return render_template('financeiro.html')

# Rotas para categorias
@app.route('/api/financeiro/categorias/entrada', methods=['GET'])
@login_required
def get_categorias_entrada():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, nome, descricao FROM categorias_entrada ORDER BY nome')
        categorias = [{'id': row[0], 'nome': row[1], 'descricao': row[2]} for row in cursor.fetchall()]
        conn.close()
        return jsonify(categorias)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/financeiro/categorias/despesa', methods=['GET'])
@login_required
def get_categorias_despesa():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, nome, descricao FROM categorias_despesa ORDER BY nome')
        categorias = [{'id': row[0], 'nome': row[1], 'descricao': row[2]} for row in cursor.fetchall()]
        conn.close()
        return jsonify(categorias)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rotas alternativas com hífen (para compatibilidade)
@app.route('/api/financeiro/categorias-entrada', methods=['GET'])
@login_required
def get_categorias_entrada_alt():
    return get_categorias_entrada()

@app.route('/api/financeiro/categorias-despesa', methods=['GET'])
@login_required
def get_categorias_despesa_alt():
    return get_categorias_despesa()

# Rotas para entradas
@app.route('/api/financeiro/entradas', methods=['GET'])
@login_required
def get_entradas():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id, e.descricao, e.valor, e.data_entrada, e.categoria_id, 
                   e.veiculo_id, e.tipo, e.observacoes, e.data_criacao,
                   c.nome as categoria_nome, v.placa, v.modelo
            FROM entradas e
            LEFT JOIN categorias_entrada c ON e.categoria_id = c.id
            LEFT JOIN veiculos v ON e.veiculo_id = v.id
            ORDER BY e.data_entrada DESC
        ''')
        
        entradas = []
        for row in cursor.fetchall():
            entradas.append({
                'id': row[0],
                'descricao': row[1],
                'valor': row[2],
                'data_entrada': row[3],
                'categoria_id': row[4],
                'veiculo_id': row[5],
                'tipo': row[6],
                'observacoes': row[7],
                'data_criacao': row[8],
                'categoria_nome': row[9],
                'veiculo_placa': row[10],
                'veiculo_modelo': row[11]
            })
        
        conn.close()
        return jsonify(entradas)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/financeiro/entrada', methods=['POST'])
@login_required
def create_entrada():
    try:
        data = request.json
        conn = sqlite3.connect(DATABASE, timeout=30.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO entradas (descricao, valor, data_entrada, categoria_id, veiculo_id, tipo, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['descricao'],
            data['valor'],
            data['data_entrada'],
            data['categoria_id'],
            data.get('veiculo_id'),
            data.get('tipo', 'Manual'),
            data.get('observacoes', '')
        ))
        
        conn.commit()
        entrada_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': entrada_id, 'message': 'Entrada cadastrada com sucesso!'})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        if conn:
            conn.close()

# Rotas para despesas
@app.route('/api/financeiro/despesas', methods=['GET'])
@login_required
def get_despesas():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.id, d.descricao, d.valor, d.data_despesa, d.categoria_id, 
                   d.veiculo_id, d.tipo, d.manutencao_id, d.observacoes, d.data_criacao,
                   c.nome as categoria_nome, v.placa, v.modelo
            FROM despesas d
            LEFT JOIN categorias_despesa c ON d.categoria_id = c.id
            LEFT JOIN veiculos v ON d.veiculo_id = v.id
            ORDER BY d.data_despesa DESC
        ''')
        
        despesas = []
        for row in cursor.fetchall():
            despesas.append({
                'id': row[0],
                'descricao': row[1],
                'valor': row[2],
                'data_despesa': row[3],
                'categoria_id': row[4],
                'veiculo_id': row[5],
                'tipo': row[6],
                'manutencao_id': row[7],
                'observacoes': row[8],
                'data_criacao': row[9],
                'categoria_nome': row[10],
                'veiculo_placa': row[11],
                'veiculo_modelo': row[12]
            })
        
        conn.close()
        return jsonify(despesas)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/financeiro/despesa', methods=['POST'])
@login_required
def create_despesa():
    try:
        data = request.json
        conn = sqlite3.connect(DATABASE, timeout=30.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO despesas (descricao, valor, data_despesa, categoria_id, veiculo_id, tipo, observacoes, manutencao_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['descricao'],
            data['valor'],
            data['data_despesa'],
            data['categoria_id'],
            data.get('veiculo_id'),
            data.get('tipo', 'Manual'),
            data.get('observacoes', ''),
            data.get('manutencao_id')
        ))
        
        conn.commit()
        despesa_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': despesa_id, 'message': 'Despesa cadastrada com sucesso!'})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        if conn:
            conn.close()

# Rota para relatórios financeiros
@app.route('/api/financeiro/resumo', methods=['GET'])
@login_required
def get_resumo_financeiro():
    try:
        periodo = request.args.get('periodo', '30')  # últimos 30 dias por padrão
        
        # Validar período (segurança)
        try:
            periodo_int = int(periodo)
            if periodo_int < 1 or periodo_int > 3650:  # Máximo 10 anos
                periodo_int = 30
        except ValueError:
            periodo_int = 30
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Total de entradas
        cursor.execute('SELECT COALESCE(SUM(valor), 0) FROM entradas WHERE data_entrada >= date("now", "-" || ? || " days")', (periodo_int,))
        total_entradas = cursor.fetchone()[0]
        
        # Total de despesas
        cursor.execute('SELECT COALESCE(SUM(valor), 0) FROM despesas WHERE data_despesa >= date("now", "-" || ? || " days")', (periodo_int,))
        total_despesas = cursor.fetchone()[0]
        
        # Entradas por categoria
        cursor.execute('''
            SELECT c.nome, COALESCE(SUM(e.valor), 0)
            FROM categorias_entrada c
            LEFT JOIN entradas e ON c.id = e.categoria_id AND e.data_entrada >= date("now", "-" || ? || " days")
            GROUP BY c.id, c.nome
            ORDER BY SUM(e.valor) DESC
        ''', (periodo_int,))
        entradas_categoria = cursor.fetchall()
        
        # Despesas por categoria
        cursor.execute('''
            SELECT c.nome, COALESCE(SUM(d.valor), 0)
            FROM categorias_despesa c
            LEFT JOIN despesas d ON c.id = d.categoria_id AND d.data_despesa >= date("now", "-" || ? || " days")
            GROUP BY c.id, c.nome
            ORDER BY SUM(d.valor) DESC
        ''', (periodo_int,))
        despesas_categoria = cursor.fetchall()
        
        # Resultado por veículo
        cursor.execute('''
            SELECT v.placa, v.modelo,
                   COALESCE(SUM(e.valor), 0) as entradas,
                   COALESCE(SUM(d.valor), 0) as despesas,
                   (COALESCE(SUM(e.valor), 0) - COALESCE(SUM(d.valor), 0)) as saldo
            FROM veiculos v
            LEFT JOIN entradas e ON v.id = e.veiculo_id AND e.data_entrada >= date("now", "-" || ? || " days")
            LEFT JOIN despesas d ON v.id = d.veiculo_id AND d.data_despesa >= date("now", "-" || ? || " days")
            GROUP BY v.id, v.placa, v.modelo
            HAVING entradas > 0 OR despesas > 0
            ORDER BY saldo DESC
        ''', (periodo_int, periodo_int))
        resultado_veiculo = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_entradas': total_entradas,
            'total_despesas': total_despesas,
            'saldo': total_entradas - total_despesas,
            'entradas_categoria': [{'categoria': row[0], 'valor': row[1]} for row in entradas_categoria],
            'despesas_categoria': [{'categoria': row[0], 'valor': row[1]} for row in despesas_categoria],
            'resultado_veiculo': [{'placa': row[0], 'modelo': row[1], 'entradas': row[2], 'despesas': row[3], 'saldo': row[4]} for row in resultado_veiculo]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# =============================================
# ROTAS DE ADMINISTRAÇÃO E GERENCIAMENTO
# =============================================

@app.route('/admin/backup')
@login_required
@admin_required
def admin_backup():
    """Criar backup do banco de dados"""
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"frota_backup_{timestamp}.db"
        backup_path = os.path.join('backups', backup_filename)
        
        # Criar diretório de backups se não existir
        os.makedirs('backups', exist_ok=True)
        
        success = db_manager.backup_database(backup_path)
        
        if success:
            log_action(current_user.id, 'BACKUP', None, None, 
                      f'Criou backup: {backup_filename}', request.remote_addr)
            return send_file(backup_path, as_attachment=True, download_name=backup_filename)
        else:
            flash('Erro ao criar backup!', 'danger')
            return redirect(url_for('dashboard'))
    except Exception as e:
        app.logger.error(f'Erro ao criar backup: {e}')
        flash(f'Erro ao criar backup: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/perfil')
@login_required
def perfil():
    """Perfil do usuário logado"""
    return render_template('perfil.html', user=current_user)

@app.route('/alterar-senha', methods=['POST'])
@login_required
def alterar_senha():
    """Alterar senha do usuário logado"""
    from auth import change_password
    
    senha_atual = request.form.get('senha_atual')
    senha_nova = request.form.get('senha_nova')
    senha_confirma = request.form.get('senha_confirma')
    
    if not all([senha_atual, senha_nova, senha_confirma]):
        flash('Todos os campos são obrigatórios!', 'danger')
        return redirect(url_for('perfil'))
    
    if senha_nova != senha_confirma:
        flash('As senhas não coincidem!', 'danger')
        return redirect(url_for('perfil'))
    
    if len(senha_nova) < 6:
        flash('A senha deve ter no mínimo 6 caracteres!', 'danger')
        return redirect(url_for('perfil'))
    
    success, message = change_password(current_user.id, senha_atual, senha_nova)
    
    if success:
        log_action(current_user.id, 'CHANGE_PASSWORD', 'usuarios', current_user.id, 
                  'Alterou sua própria senha', request.remote_addr)
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('perfil'))

if __name__ == '__main__':
    init_db()
    # Configuração para produção
    import os
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)