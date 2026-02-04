"""
Migração 007: Criar índices de performance multi-tenancy
=========================================================

OBJETIVO: Otimizar queries multi-tenant e garantir performance

MUDANÇAS:
- Cria índices compostos começando por empresa_id
- Otimiza consultas mais comuns do sistema
- Prepara para escala de múltiplas empresas

REVERSÍVEL: Sim (DROP INDEX)
SEGURO PARA PRODUÇÃO: Sim (apenas índices, não altera dados)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Cria índices de performance para multi-tenancy"""
    
    name = "Criar índices de performance multi-tenancy"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Criando índices de performance...")
            
            # Índices para tabela veiculos
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_veiculos_empresa_status 
                ON veiculos(empresa_id, status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_veiculos_empresa_placa 
                ON veiculos(empresa_id, placa)
            """)
            
            # Índices para tabela manutencoes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_manutencoes_empresa_status 
                ON manutencoes(empresa_id, status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_manutencoes_empresa_data 
                ON manutencoes(empresa_id, data_agendada DESC)
            """ if self.is_postgres else """
                CREATE INDEX IF NOT EXISTS idx_manutencoes_empresa_data 
                ON manutencoes(empresa_id, data_agendada)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_manutencoes_empresa_veiculo 
                ON manutencoes(empresa_id, veiculo_id)
            """)
            
            # Índices para tabela pecas (verifica se tem coluna ativo)
            try:
                if self.is_postgres:
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='pecas' AND column_name='ativo'
                    """)
                else:
                    cursor.execute("PRAGMA table_info(pecas)")
                    columns = [col[1] for col in cursor.fetchall()]
                    has_ativo = 'ativo' in columns
                
                if self.is_postgres and cursor.fetchone() or not self.is_postgres and has_ativo:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_pecas_empresa_ativo 
                        ON pecas(empresa_id, ativo)
                    """)
            except:
                pass  # Coluna ativo pode não existir
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pecas_empresa_codigo 
                ON pecas(empresa_id, codigo)
            """)
            
            # Índices para tabela fornecedores
            try:
                if self.is_postgres:
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='fornecedores' AND column_name='ativo'
                    """)
                else:
                    cursor.execute("PRAGMA table_info(fornecedores)")
                    columns = [col[1] for col in cursor.fetchall()]
                    has_ativo = 'ativo' in columns
                
                if self.is_postgres and cursor.fetchone() or not self.is_postgres and has_ativo:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_fornecedores_empresa_ativo 
                        ON fornecedores(empresa_id, ativo)
                    """)
            except:
                pass
            
            # Índices para tabela tecnicos (se existir)
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tecnicos_empresa_status 
                    ON tecnicos(empresa_id, status)
                """)
            except:
                pass  # Tabela pode não existir
            
            # Índices para tabela usuarios
            try:
                if self.is_postgres:
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='usuarios' AND column_name='ativo'
                    """)
                else:
                    cursor.execute("PRAGMA table_info(usuarios)")
                    columns = [col[1] for col in cursor.fetchall()]
                    has_ativo = 'ativo' in columns
                
                if self.is_postgres and cursor.fetchone() or not self.is_postgres and has_ativo:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_usuarios_empresa_ativo 
                        ON usuarios(empresa_id, ativo)
                    """)
            except:
                pass
            
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_usuarios_empresa_role 
                    ON usuarios(empresa_id, role)
                """)
            except:
                pass
            
            # Índices para tabelas financeiras (se existirem)
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_financeiro_entradas_empresa_data 
                    ON financeiro_entradas(empresa_id, data_entrada DESC)
                """ if self.is_postgres else """
                    CREATE INDEX IF NOT EXISTS idx_financeiro_entradas_empresa_data 
                    ON financeiro_entradas(empresa_id, data_entrada)
                """)
            except:
                pass
            
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_financeiro_despesas_empresa_data 
                    ON financeiro_despesas(empresa_id, data_despesa DESC)
                """ if self.is_postgres else """
                    CREATE INDEX IF NOT EXISTS idx_financeiro_despesas_empresa_data 
                    ON financeiro_despesas(empresa_id, data_despesa)
                """)
            except:
                pass
            
            # Índice específico para busca por tipo de empresa
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_empresas_ativo_tipo 
                    ON empresas(ativo, tipo_operacao) 
                    WHERE ativo = TRUE
                """ if self.is_postgres else """
                    CREATE INDEX IF NOT EXISTS idx_empresas_ativo_tipo 
                    ON empresas(ativo, tipo_operacao)
                """)
            except:
                pass
            
            conn.commit()
            print("   ✅ Índices de performance criados com sucesso")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao aplicar migração 007: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Removendo índices de performance...")
            
            indices = [
                'idx_veiculos_empresa_status',
                'idx_veiculos_empresa_placa',
                'idx_manutencoes_empresa_status',
                'idx_manutencoes_empresa_data',
                'idx_manutencoes_empresa_veiculo',
                'idx_pecas_empresa_ativo',
                'idx_pecas_empresa_codigo',
                'idx_fornecedores_empresa_ativo',
                'idx_tecnicos_empresa_ativo',
                'idx_usuarios_empresa_ativo',
                'idx_usuarios_empresa_role',
                'idx_financeiro_entradas_empresa_data',
                'idx_financeiro_despesas_empresa_data',
                'idx_empresas_ativo_tipo'
            ]
            
            for idx in indices:
                try:
                    cursor.execute(f"DROP INDEX IF EXISTS {idx}")
                except:
                    pass  # Índice pode não existir
            
            conn.commit()
            print("   ✅ Índices removidos")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao reverter migração 007: {e}")
        finally:
            cursor.close()
            conn.close()
