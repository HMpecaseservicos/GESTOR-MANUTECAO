"""
ETAPA 14 — AUTOMAÇÕES E CRON JOBS
=================================

Módulo para executar verificações automáticas periódicas e gerar
notificações proativas sem depender de ações do usuário.

PostgreSQL Only - Otimizado para SaaS Fly.io

TAREFAS:
- A cada 1 hora:
  * Manutenções atrasadas (status != FINALIZADO/Concluída AND data_prevista < NOW())
  * Serviços finalizados sem faturamento (status = FINALIZADO AND financeiro_lancado_em IS NULL)
  
- Diariamente:
  * Verificar limites próximos (80%)

PRINCÍPIOS:
- Funções idempotentes (não duplicar notificações)
- Sempre filtrar por empresa_id (multi-tenancy)
- Usar create_notification() do empresa_helpers
- Logs claros para monitoramento
"""

import os
import sys
from datetime import datetime, timedelta
import psycopg2

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

# =============================================
# FUNÇÕES AUXILIARES
# =============================================

def get_db_connection():
    """Retorna conexão com o banco de dados PostgreSQL"""
    return psycopg2.connect(Config.DATABASE_URL)


def log_cron(message, level="INFO"):
    """Log formatado para cron jobs"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "START": "🚀",
        "END": "🏁"
    }.get(level, "📌")
    
    print(f"[CRON {timestamp}] {emoji} {message}", flush=True)


def notificacao_existe(cursor, empresa_id, tipo, titulo_like, horas=24):
    """
    Verifica se já existe notificação similar nas últimas X horas.
    Evita duplicação de notificações.
    
    Args:
        cursor: Cursor do banco
        empresa_id: ID da empresa
        tipo: Tipo da notificação
        titulo_like: Parte do título para busca (LIKE %titulo%)
        horas: Janela de tempo em horas (default 24h)
    
    Returns:
        bool: True se existe notificação similar
    """
    cursor.execute("""
        SELECT COUNT(*) FROM notificacoes 
        WHERE empresa_id = %s 
        AND tipo = %s 
        AND titulo LIKE %s
        AND created_at > NOW() - INTERVAL '%s hours'
    """, (empresa_id, tipo, f"%{titulo_like}%", horas))
    
    return cursor.fetchone()[0] > 0


def criar_notificacao(cursor, empresa_id, tipo, titulo, mensagem, link=None):
    """Cria notificação diretamente (sem usar import de empresa_helpers para evitar circular)"""
    cursor.execute("""
        INSERT INTO notificacoes (empresa_id, usuario_id, tipo, titulo, mensagem, link, lida)
        VALUES (%s, NULL, %s, %s, %s, %s, false)
    """, (empresa_id, tipo, titulo[:200], mensagem, link))


# =============================================
# TAREFA: MANUTENÇÕES ATRASADAS (HORÁRIA)
# =============================================

def verificar_manutencoes_atrasadas():
    """
    Verifica manutenções com data prevista no passado que ainda não foram finalizadas.
    
    Para FROTA: status NOT IN ('Concluída', 'Cancelada')
    Para SERVICO: status NOT IN ('FINALIZADO', 'FATURADO', 'CANCELADO')
    
    Cria notificação MANUTENCAO_ATRASADA se não existir nas últimas 24h.
    """
    log_cron("Iniciando verificação de manutenções atrasadas...", "START")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    total_notificadas = 0
    
    try:
        # Buscar empresas ativas
        cursor.execute("SELECT id, nome, tipo_operacao FROM empresas WHERE ativo = true")
        empresas = cursor.fetchall()
        
        for empresa in empresas:
            empresa_id = empresa[0]
            empresa_nome = empresa[1]
            tipo_operacao = empresa[2] or 'FROTA'
            
            # Definir status de não finalização baseado no tipo
            if tipo_operacao == 'SERVICO':
                status_pendentes = "('EM_EXECUCAO', 'APROVADO', 'ORCAMENTO', 'RASCUNHO', 'Agendada', 'Em Andamento')"
            else:
                status_pendentes = "('Agendada', 'Em Andamento')"
            
            # Buscar manutenções atrasadas
            query = f"""
                SELECT m.id, m.tipo, m.data_agendada, v.placa, v.modelo
                FROM manutencoes m
                LEFT JOIN veiculos v ON m.veiculo_id = v.id
                WHERE m.empresa_id = %s
                AND m.status IN {status_pendentes}
                AND m.data_agendada < CURRENT_DATE
                ORDER BY m.data_agendada ASC
                LIMIT 50
            """
            cursor.execute(query, (empresa_id,))
            manutencoes_atrasadas = cursor.fetchall()
            
            if not manutencoes_atrasadas:
                continue
            
            # Agrupar por veículo para não enviar muitas notificações
            count = len(manutencoes_atrasadas)
            
            # Verificar se já notificamos sobre isso hoje
            titulo_check = f"{count} manutenç"
            if notificacao_existe(cursor, empresa_id, 'MANUTENCAO_ATRASADA', titulo_check, horas=24):
                log_cron(f"  Empresa {empresa_nome}: já notificada sobre {count} manutenções atrasadas")
                continue
            
            # Criar notificação
            titulo = f"⏰ {count} manutenção(ões) atrasada(s)"
            
            if count == 1:
                m = manutencoes_atrasadas[0]
                placa = m[3] or 'Sem placa'
                mensagem = f"Manutenção '{m[1]}' do veículo {placa} estava agendada para {m[2]} e não foi concluída."
            else:
                mais_antiga = manutencoes_atrasadas[0]
                placa = mais_antiga[3] or 'Sem placa'
                mensagem = f"Você tem {count} manutenções pendentes. A mais antiga ({mais_antiga[1]} - {placa}) estava agendada para {mais_antiga[2]}."
            
            criar_notificacao(cursor, empresa_id, 'MANUTENCAO_ATRASADA', titulo, mensagem, link='/manutencao')
            total_notificadas += 1
            log_cron(f"  Empresa {empresa_nome}: notificação criada ({count} manutenções atrasadas)")
        
        conn.commit()
        log_cron(f"Manutenções atrasadas: {total_notificadas} empresas notificadas", "SUCCESS")
        
    except Exception as e:
        log_cron(f"Erro ao verificar manutenções atrasadas: {e}", "ERROR")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return total_notificadas


# =============================================
# TAREFA: SERVIÇOS SEM FATURAMENTO (HORÁRIA)
# =============================================

def verificar_servicos_sem_faturamento():
    """
    Verifica serviços finalizados que ainda não foram lançados no financeiro.
    
    Condição: status = 'FINALIZADO' AND financeiro_lancado_em IS NULL
    
    Apenas para empresas tipo SERVICO.
    Cria notificação SERVICO_SEM_FATURAMENTO se não existir nas últimas 24h.
    """
    log_cron("Iniciando verificação de serviços sem faturamento...", "START")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    total_notificadas = 0
    
    try:
        # Buscar empresas SERVICO ativas
        cursor.execute("""
            SELECT id, nome FROM empresas 
            WHERE ativo = true AND tipo_operacao = 'SERVICO'
        """)
        empresas = cursor.fetchall()
        
        for empresa in empresas:
            empresa_id = empresa[0]
            empresa_nome = empresa[1]
            
            # Buscar manutenções finalizadas sem faturamento
            cursor.execute("""
                SELECT m.id, m.tipo, m.data_realizada, v.placa, m.valor_total_servicos
                FROM manutencoes m
                LEFT JOIN veiculos v ON m.veiculo_id = v.id
                WHERE m.empresa_id = %s
                AND m.status = 'FINALIZADO'
                AND m.financeiro_lancado_em IS NULL
                ORDER BY m.data_realizada DESC
                LIMIT 50
            """, (empresa_id,))
            servicos_pendentes = cursor.fetchall()
            
            if not servicos_pendentes:
                continue
            
            count = len(servicos_pendentes)
            
            # Calcular valor total pendente
            valor_total = sum(float(s[4] or 0) for s in servicos_pendentes)
            
            # Verificar se já notificamos sobre isso hoje
            titulo_check = f"{count} serviço"
            if notificacao_existe(cursor, empresa_id, 'SERVICO_SEM_FATURAMENTO', titulo_check, horas=24):
                log_cron(f"  Empresa {empresa_nome}: já notificada sobre {count} serviços pendentes")
                continue
            
            # Criar notificação
            titulo = f"💰 {count} serviço(s) sem faturamento"
            
            if count == 1:
                s = servicos_pendentes[0]
                placa = s[3] or 'Sem placa'
                valor = s[4] or 0
                mensagem = f"Serviço '{s[1]}' ({placa}) foi finalizado mas não lançado no financeiro. Valor: R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            else:
                mensagem = f"Você tem {count} serviços finalizados aguardando lançamento no financeiro. Valor total: R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            criar_notificacao(cursor, empresa_id, 'SERVICO_SEM_FATURAMENTO', titulo, mensagem, link='/financeiro')
            total_notificadas += 1
            log_cron(f"  Empresa {empresa_nome}: notificação criada ({count} serviços, R$ {valor_total:.2f})")
        
        conn.commit()
        log_cron(f"Serviços sem faturamento: {total_notificadas} empresas notificadas", "SUCCESS")
        
    except Exception as e:
        log_cron(f"Erro ao verificar serviços sem faturamento: {e}", "ERROR")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return total_notificadas


# =============================================
# TAREFA: VERIFICAR LIMITES 80% (DIÁRIA)
# =============================================

def verificar_limites_proximos():
    """
    Verifica empresas próximas de atingir o limite do plano (80%).
    
    Recursos verificados:
    - Clientes
    - Veículos  
    - Usuários
    
    Cria notificação LIMITE_AVISO se não existir nas últimas 24h.
    """
    log_cron("Iniciando verificação de limites próximos (80%)...", "START")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    total_notificadas = 0
    
    try:
        # Buscar empresas ativas com limites definidos
        cursor.execute("""
            SELECT id, nome, plano, limite_clientes, limite_veiculos, limite_usuarios
            FROM empresas 
            WHERE ativo = true
        """)
        empresas = cursor.fetchall()
        
        for empresa in empresas:
            empresa_id = empresa[0]
            empresa_nome = empresa[1]
            plano = empresa[2] or 'BASICO'
            limite_clientes = empresa[3]
            limite_veiculos = empresa[4]
            limite_usuarios = empresa[5]
            
            avisos = []
            
            # Verificar clientes
            if limite_clientes:
                cursor.execute("""
                    SELECT COUNT(*) FROM clientes 
                    WHERE empresa_id = %s AND ativo = true
                """, (empresa_id,))
                total_clientes = cursor.fetchone()[0]
                percentual = (total_clientes / limite_clientes) * 100
                
                if percentual >= 80 and percentual < 100:
                    avisos.append(f"Clientes: {total_clientes}/{limite_clientes} ({percentual:.0f}%)")
            
            # Verificar veículos
            if limite_veiculos:
                cursor.execute("""
                    SELECT COUNT(*) FROM veiculos 
                    WHERE empresa_id = %s AND ativo = true
                """, (empresa_id,))
                total_veiculos = cursor.fetchone()[0]
                percentual = (total_veiculos / limite_veiculos) * 100
                
                if percentual >= 80 and percentual < 100:
                    avisos.append(f"Veículos: {total_veiculos}/{limite_veiculos} ({percentual:.0f}%)")
            
            # Verificar usuários
            if limite_usuarios:
                cursor.execute("""
                    SELECT COUNT(*) FROM usuarios 
                    WHERE empresa_id = %s AND ativo = true
                """, (empresa_id,))
                total_usuarios = cursor.fetchone()[0]
                percentual = (total_usuarios / limite_usuarios) * 100
                
                if percentual >= 80 and percentual < 100:
                    avisos.append(f"Usuários: {total_usuarios}/{limite_usuarios} ({percentual:.0f}%)")
            
            if not avisos:
                continue
            
            # Verificar se já notificamos sobre isso hoje
            titulo_check = "Limite do plano"
            if notificacao_existe(cursor, empresa_id, 'LIMITE_AVISO', titulo_check, horas=24):
                log_cron(f"  Empresa {empresa_nome}: já notificada sobre limites")
                continue
            
            # Criar notificação
            titulo = f"⚠️ Limite do plano {plano} próximo"
            mensagem = "Recursos chegando ao limite:\n• " + "\n• ".join(avisos)
            mensagem += "\n\nConsidere fazer upgrade do seu plano."
            
            criar_notificacao(cursor, empresa_id, 'LIMITE_AVISO', titulo, mensagem, link='/minha-empresa')
            total_notificadas += 1
            log_cron(f"  Empresa {empresa_nome}: notificação criada (limites: {', '.join(avisos)})")
        
        conn.commit()
        log_cron(f"Limites próximos: {total_notificadas} empresas notificadas", "SUCCESS")
        
    except Exception as e:
        log_cron(f"Erro ao verificar limites: {e}", "ERROR")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return total_notificadas


# =============================================
# EXECUTOR DE CRON JOBS
# =============================================

def executar_tarefas_horarias():
    """Executa todas as tarefas que rodam a cada hora"""
    log_cron("=" * 60, "START")
    log_cron("INICIANDO TAREFAS HORÁRIAS", "START")
    log_cron("=" * 60, "START")
    
    resultados = {}
    
    try:
        resultados['manutencoes_atrasadas'] = verificar_manutencoes_atrasadas()
        resultados['servicos_sem_faturamento'] = verificar_servicos_sem_faturamento()
        
        log_cron("=" * 60, "END")
        log_cron(f"TAREFAS HORÁRIAS CONCLUÍDAS: {resultados}", "END")
        log_cron("=" * 60, "END")
        
    except Exception as e:
        log_cron(f"Erro nas tarefas horárias: {e}", "ERROR")
    
    return resultados


def executar_tarefas_diarias():
    """Executa todas as tarefas que rodam diariamente"""
    log_cron("=" * 60, "START")
    log_cron("INICIANDO TAREFAS DIÁRIAS", "START")
    log_cron("=" * 60, "START")
    
    resultados = {}
    
    try:
        resultados['limites_proximos'] = verificar_limites_proximos()
        
        # Também executar tarefas horárias
        resultados.update(executar_tarefas_horarias())
        
        log_cron("=" * 60, "END")
        log_cron(f"TAREFAS DIÁRIAS CONCLUÍDAS: {resultados}", "END")
        log_cron("=" * 60, "END")
        
    except Exception as e:
        log_cron(f"Erro nas tarefas diárias: {e}", "ERROR")
    
    return resultados


def executar_todas_tarefas():
    """Executa todas as tarefas (útil para teste)"""
    return executar_tarefas_diarias()


# =============================================
# CLI PARA EXECUÇÃO MANUAL
# =============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Executor de Cron Jobs do Sistema')
    parser.add_argument('--hourly', action='store_true', help='Executar tarefas horárias')
    parser.add_argument('--daily', action='store_true', help='Executar tarefas diárias')
    parser.add_argument('--all', action='store_true', help='Executar todas as tarefas')
    parser.add_argument('--manutencoes', action='store_true', help='Verificar manutenções atrasadas')
    parser.add_argument('--faturamento', action='store_true', help='Verificar serviços sem faturamento')
    parser.add_argument('--limites', action='store_true', help='Verificar limites próximos')
    
    args = parser.parse_args()
    
    if args.hourly:
        executar_tarefas_horarias()
    elif args.daily:
        executar_tarefas_diarias()
    elif args.all:
        executar_todas_tarefas()
    elif args.manutencoes:
        verificar_manutencoes_atrasadas()
    elif args.faturamento:
        verificar_servicos_sem_faturamento()
    elif args.limites:
        verificar_limites_proximos()
    else:
        print("Uso: python cron_jobs.py [--hourly|--daily|--all|--manutencoes|--faturamento|--limites]")
        print("\nExemplos:")
        print("  python cron_jobs.py --hourly    # Tarefas de hora em hora")
        print("  python cron_jobs.py --daily     # Tarefas diárias")
        print("  python cron_jobs.py --all       # Todas as tarefas")
