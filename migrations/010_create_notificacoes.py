"""
Migração 010: Criar tabela de notificações
==========================================

OBJETIVO: Sistema de notificações internas para alertas importantes

TABELA NOTIFICACOES:
- id: Identificador único
- empresa_id: Multi-tenant (FK)
- usuario_id: Destinatário específico (NULL = todos da empresa)
- tipo: Categoria (LIMITE, MANUTENCAO, SERVICO, USUARIO, SISTEMA)
- titulo: Título curto
- mensagem: Descrição detalhada
- lida: Boolean
- link: URL opcional para ação
- created_at: Data de criação

TIPOS DE NOTIFICAÇÃO:
- LIMITE_AVISO: 80% do limite atingido
- LIMITE_BLOQUEIO: 100% do limite atingido
- MANUTENCAO_ATRASADA: Manutenção com data prevista ultrapassada
- SERVICO_SEM_FATURAMENTO: Serviço finalizado sem lançar financeiro
- USUARIO_CRIADO: Novo usuário adicionado
- ACAO_BLOQUEADA: Tentativa de ação bloqueada por limite
- SISTEMA: Avisos gerais do sistema

REVERSÍVEL: Sim (DROP TABLE)
SEGURO PARA PRODUÇÃO: Sim
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Criar tabela de notificações"""
    
    name = "Criar tabela notificacoes"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Verificando se tabela notificacoes existe...")
            
            if self.is_postgres:
                # PostgreSQL
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'notificacoes'
                    )
                """)
                exists = cursor.fetchone()[0]
                
                if exists:
                    print("   ⚠️  Tabela notificacoes já existe. Pulando...")
                else:
                    print("   📝 Criando tabela notificacoes...")
                    cursor.execute("""
                        CREATE TABLE notificacoes (
                            id SERIAL PRIMARY KEY,
                            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                            tipo VARCHAR(50) NOT NULL DEFAULT 'SISTEMA',
                            titulo VARCHAR(200) NOT NULL,
                            mensagem TEXT,
                            lida BOOLEAN DEFAULT FALSE,
                            link VARCHAR(500),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    print("   ✅ Tabela notificacoes criada!")
                    
                    # Criar índices
                    print("   📝 Criando índices...")
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_notificacoes_empresa 
                        ON notificacoes(empresa_id)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario 
                        ON notificacoes(usuario_id)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_notificacoes_lida 
                        ON notificacoes(empresa_id, lida)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_notificacoes_created 
                        ON notificacoes(created_at DESC)
                    """)
                    print("   ✅ Índices criados!")
                
            else:
                # SQLite
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='notificacoes'
                """)
                
                if cursor.fetchone():
                    print("   ⚠️  Tabela notificacoes já existe. Pulando...")
                else:
                    print("   📝 Criando tabela notificacoes...")
                    cursor.execute("""
                        CREATE TABLE notificacoes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            empresa_id INTEGER NOT NULL,
                            usuario_id INTEGER,
                            tipo TEXT NOT NULL DEFAULT 'SISTEMA',
                            titulo TEXT NOT NULL,
                            mensagem TEXT,
                            lida INTEGER DEFAULT 0,
                            link TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                        )
                    """)
                    print("   ✅ Tabela notificacoes criada!")
                    
                    # Índices SQLite
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notificacoes_empresa ON notificacoes(empresa_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario ON notificacoes(usuario_id)")
                    print("   ✅ Índices criados!")
            
            conn.commit()
            print("   ✅ Migração 010 concluída com sucesso!")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"   ❌ Erro na migração: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                cursor.execute("DROP TABLE IF EXISTS notificacoes CASCADE")
            else:
                cursor.execute("DROP TABLE IF EXISTS notificacoes")
            
            conn.commit()
            print("   ✅ Tabela notificacoes removida!")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"   ❌ Erro ao reverter migração: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
