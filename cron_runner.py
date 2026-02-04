"""
CRON RUNNER - Executor de tarefas agendadas em background
==========================================================

Este script roda em background no container e executa as tarefas automáticas
do sistema em intervalos definidos.

CONFIGURAÇÃO:
- Tarefas horárias: a cada 1 hora
- Tarefas diárias: uma vez ao dia às 06:00

USO:
  python cron_runner.py &
  
Ou via Procfile com process type 'worker'
"""

import time
import threading
import signal
import sys
from datetime import datetime, timedelta

# Configuração dos intervalos (em segundos)
INTERVALO_HORARIO = 3600  # 1 hora
HORA_TAREFA_DIARIA = 6    # 06:00 da manhã

# Flag para controlar o loop
rodando = True


def log(message, level="INFO"):
    """Log formatado"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "START": "🚀",
    }.get(level, "📌")
    print(f"[CRON_RUNNER {timestamp}] {emoji} {message}", flush=True)


def signal_handler(signum, frame):
    """Handler para sinais de interrupção"""
    global rodando
    log("Recebido sinal de interrupção. Encerrando...", "WARNING")
    rodando = False


def executar_tarefa_segura(nome, funcao):
    """Executa uma tarefa com tratamento de erro"""
    try:
        log(f"Executando: {nome}", "START")
        resultado = funcao()
        log(f"Concluído: {nome} -> {resultado}", "SUCCESS")
        return resultado
    except Exception as e:
        log(f"Erro em {nome}: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return None


def tarefa_horaria():
    """Thread para tarefas horárias"""
    global rodando
    
    # Import aqui para evitar problemas de carregamento
    from cron_jobs import executar_tarefas_horarias
    
    log("Thread de tarefas horárias iniciada")
    
    # Aguardar 5 minutos após inicialização para primeira execução
    # (permite que o app suba completamente)
    time.sleep(300)
    
    while rodando:
        try:
            executar_tarefa_segura("Tarefas Horárias", executar_tarefas_horarias)
        except Exception as e:
            log(f"Erro crítico na thread horária: {e}", "ERROR")
        
        # Aguardar próximo intervalo
        for _ in range(INTERVALO_HORARIO):
            if not rodando:
                break
            time.sleep(1)


def tarefa_diaria():
    """Thread para tarefas diárias"""
    global rodando
    
    # Import aqui para evitar problemas de carregamento
    from cron_jobs import verificar_limites_proximos
    
    log("Thread de tarefas diárias iniciada")
    
    ultima_execucao = None
    
    while rodando:
        try:
            agora = datetime.now()
            
            # Verificar se é hora de executar (06:00)
            if agora.hour == HORA_TAREFA_DIARIA:
                # Verificar se já executou hoje
                if ultima_execucao is None or ultima_execucao.date() < agora.date():
                    executar_tarefa_segura("Verificação de Limites (Diária)", verificar_limites_proximos)
                    ultima_execucao = agora
            
        except Exception as e:
            log(f"Erro crítico na thread diária: {e}", "ERROR")
        
        # Verificar a cada 5 minutos
        for _ in range(300):
            if not rodando:
                break
            time.sleep(1)


def main():
    """Função principal do runner"""
    global rodando
    
    # Registrar handlers de sinal
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    log("=" * 60, "START")
    log("CRON RUNNER INICIADO", "START")
    log(f"Intervalo horário: {INTERVALO_HORARIO}s ({INTERVALO_HORARIO/3600:.1f}h)")
    log(f"Tarefa diária às: {HORA_TAREFA_DIARIA}:00")
    log("=" * 60, "START")
    
    # Criar threads
    thread_horaria = threading.Thread(target=tarefa_horaria, daemon=True, name="cron_hourly")
    thread_diaria = threading.Thread(target=tarefa_diaria, daemon=True, name="cron_daily")
    
    # Iniciar threads
    thread_horaria.start()
    thread_diaria.start()
    
    log("Threads de cron iniciadas. Aguardando...")
    
    # Loop principal
    try:
        while rodando:
            time.sleep(10)
            
            # Verificar se threads ainda estão vivas
            if not thread_horaria.is_alive():
                log("Thread horária morreu! Reiniciando...", "WARNING")
                thread_horaria = threading.Thread(target=tarefa_horaria, daemon=True, name="cron_hourly")
                thread_horaria.start()
            
            if not thread_diaria.is_alive():
                log("Thread diária morreu! Reiniciando...", "WARNING")
                thread_diaria = threading.Thread(target=tarefa_diaria, daemon=True, name="cron_daily")
                thread_diaria.start()
                
    except KeyboardInterrupt:
        log("Interrupção por teclado", "WARNING")
    finally:
        rodando = False
        log("CRON RUNNER ENCERRADO", "INFO")


if __name__ == "__main__":
    main()
