"""
Migração 009: Adicionar RBAC (roles) e campos de planos SaaS
=============================================================

OBJETIVO: Preparar sistema para comercialização SaaS

MUDANÇAS EM USUARIOS:
- Adiciona coluna role VARCHAR(20) DEFAULT 'OPERADOR'
- Valores permitidos: 'ADMIN', 'OPERADOR'
- ADMIN: acesso total dentro da empresa
- OPERADOR: acesso limitado (visualização, cadastros simples)

MUDANÇAS EM EMPRESAS:
- Adiciona coluna plano VARCHAR(20) DEFAULT 'BASICO'
- Adiciona coluna limite_clientes INTEGER DEFAULT 50
- Adiciona coluna limite_veiculos INTEGER DEFAULT 50
- Adiciona coluna limite_usuarios INTEGER DEFAULT 3

PLANOS PREVISTOS (não implementa cobrança):
- BASICO: 50 clientes, 50 veículos, 3 usuários
- PROFISSIONAL: 200 clientes, 200 veículos, 10 usuários
- ENTERPRISE: ilimitado (NULL = sem limite)

REVERSÍVEL: Sim (DROP COLUMNs)
SEGURO PARA PRODUÇÃO: Sim (ADD COLUMN com defaults)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Adiciona RBAC e campos de planos SaaS"""
    
    name = "Adicionar RBAC (roles) e planos SaaS"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # ============================================
            # PARTE 1: ADICIONAR ROLE EM USUARIOS
            # ============================================
            print("   📝 [USUARIOS] Verificando coluna role...")
            
            if self.is_postgres:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'usuarios' AND column_name = 'role'
                """)
            else:
                cursor.execute("PRAGMA table_info(usuarios)")
                columns = [row[1] for row in cursor.fetchall()]
                has_role = 'role' in columns
            
            if self.is_postgres:
                has_role = cursor.fetchone() is not None
            
            if has_role:
                print("   ⚠️  Coluna role já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna role...")
                if self.is_postgres:
                    cursor.execute("""
                        ALTER TABLE usuarios 
                        ADD COLUMN role VARCHAR(20) DEFAULT 'OPERADOR' NOT NULL
                    """)
                else:
                    cursor.execute("""
                        ALTER TABLE usuarios 
                        ADD COLUMN role TEXT DEFAULT 'OPERADOR' NOT NULL
                    """)
                print("   ✅ Coluna role adicionada!")
                
                # O primeiro usuário de cada empresa vira ADMIN
                print("   📝 Promovendo primeiro usuário de cada empresa para ADMIN...")
                if self.is_postgres:
                    cursor.execute("""
                        UPDATE usuarios u
                        SET role = 'ADMIN'
                        WHERE u.id = (
                            SELECT MIN(u2.id) 
                            FROM usuarios u2 
                            WHERE u2.empresa_id = u.empresa_id
                        )
                    """)
                else:
                    cursor.execute("""
                        UPDATE usuarios
                        SET role = 'ADMIN'
                        WHERE id IN (
                            SELECT MIN(id) FROM usuarios GROUP BY empresa_id
                        )
                    """)
                print("   ✅ Primeiros usuários promovidos a ADMIN!")
            
            # ============================================
            # PARTE 2: ADICIONAR CAMPOS DE PLANO EM EMPRESAS
            # ============================================
            print("   📝 [EMPRESAS] Verificando colunas de planos...")
            
            # Lista de colunas a adicionar com seus defaults
            plan_columns = [
                ("plano", "VARCHAR(20)", "'BASICO'", "TEXT", "'BASICO'"),
                ("limite_clientes", "INTEGER", "50", "INTEGER", "50"),
                ("limite_veiculos", "INTEGER", "50", "INTEGER", "50"),
                ("limite_usuarios", "INTEGER", "3", "INTEGER", "3"),
            ]
            
            for col_name, pg_type, pg_default, sqlite_type, sqlite_default in plan_columns:
                if self.is_postgres:
                    cursor.execute(f"""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = 'empresas' AND column_name = '{col_name}'
                    """)
                    exists = cursor.fetchone() is not None
                else:
                    cursor.execute("PRAGMA table_info(empresas)")
                    columns = [row[1] for row in cursor.fetchall()]
                    exists = col_name in columns
                
                if exists:
                    print(f"   ⚠️  Coluna {col_name} já existe. Pulando...")
                else:
                    print(f"   📝 Adicionando coluna {col_name}...")
                    if self.is_postgres:
                        cursor.execute(f"""
                            ALTER TABLE empresas 
                            ADD COLUMN {col_name} {pg_type} DEFAULT {pg_default}
                        """)
                    else:
                        cursor.execute(f"""
                            ALTER TABLE empresas 
                            ADD COLUMN {col_name} {sqlite_type} DEFAULT {sqlite_default}
                        """)
                    print(f"   ✅ Coluna {col_name} adicionada!")
            
            conn.commit()
            print("   ✅ Migração 009 concluída com sucesso!")
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
                # Remover colunas de empresas
                print("   📝 Removendo colunas de planos de empresas...")
                for col in ['plano', 'limite_clientes', 'limite_veiculos', 'limite_usuarios']:
                    try:
                        cursor.execute(f"ALTER TABLE empresas DROP COLUMN IF EXISTS {col}")
                        print(f"   ✅ Coluna {col} removida!")
                    except:
                        pass
                
                # Remover coluna role de usuarios
                print("   📝 Removendo coluna role de usuarios...")
                cursor.execute("ALTER TABLE usuarios DROP COLUMN IF EXISTS role")
                print("   ✅ Coluna role removida!")
                
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"   ❌ Erro ao reverter migração: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
