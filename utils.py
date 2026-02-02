"""
Módulo de Utilitários - Sistema de Gestão de Manutenção
======================================================

Este módulo contém funções utilitárias e helpers usados em todo o sistema.
"""

from datetime import datetime, date
from decimal import Decimal
import re
import os

class DateUtils:
    """Utilitários para manipulação de datas"""
    
    @staticmethod
    def format_date_br(date_obj):
        """Formata data no padrão brasileiro (DD/MM/AAAA)"""
        if not date_obj:
            return "-"
        
        if isinstance(date_obj, str):
            try:
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
            except ValueError:
                return date_obj
        
        return date_obj.strftime("%d/%m/%Y")
    
    @staticmethod
    def format_datetime_br(datetime_obj):
        """Formata data e hora no padrão brasileiro"""
        if not datetime_obj:
            return "-"
        
        if isinstance(datetime_obj, str):
            try:
                datetime_obj = datetime.fromisoformat(datetime_obj.replace('Z', '+00:00'))
            except ValueError:
                return datetime_obj
        
        return datetime_obj.strftime("%d/%m/%Y %H:%M")
    
    @staticmethod
    def days_until(target_date):
        """Calcula quantos dias faltam para uma data"""
        if not target_date:
            return None
        
        if isinstance(target_date, str):
            try:
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                return None
        
        today = date.today()
        delta = target_date - today
        return delta.days

class CurrencyUtils:
    """Utilitários para formatação de moeda"""
    
    @staticmethod
    def format_currency(value):
        """Formata valor como moeda brasileira"""
        if value is None:
            return "R$ 0,00"
        
        try:
            value = float(value)
            return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return "R$ 0,00"
    
    @staticmethod
    def parse_currency(currency_str):
        """Converte string de moeda para float"""
        if not currency_str:
            return 0.0
        
        # Remove símbolos e converte vírgula para ponto
        clean_str = re.sub(r'[R$\s]', '', str(currency_str))
        clean_str = clean_str.replace('.', '').replace(',', '.')
        
        try:
            return float(clean_str)
        except ValueError:
            return 0.0

class ValidationUtils:
    """Utilitários para validação de dados"""
    
    @staticmethod
    def validate_email(email):
        """Valida formato de email"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone):
        """Valida formato de telefone brasileiro"""
        if not phone:
            return False
        
        # Remove caracteres não numéricos
        clean_phone = re.sub(r'\D', '', phone)
        
        # Verifica se tem 10 ou 11 dígitos
        return len(clean_phone) in [10, 11]
    
    @staticmethod
    def validate_placa(placa):
        """Valida formato de placa de veículo (Mercosul e antiga)"""
        if not placa:
            return False
        
        placa = placa.upper().replace('-', '').replace(' ', '')
        
        # Formato antigo: ABC1234
        pattern_old = r'^[A-Z]{3}[0-9]{4}$'
        
        # Formato Mercosul: ABC1D23
        pattern_mercosul = r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'
        
        return re.match(pattern_old, placa) or re.match(pattern_mercosul, placa)
    
    @staticmethod
    def format_placa(placa):
        """Formata placa no padrão XXX-XXXX"""
        if not placa:
            return ""
        
        placa = placa.upper().replace('-', '').replace(' ', '')
        
        if len(placa) == 7:
            return f"{placa[:3]}-{placa[3:]}"
        
        return placa
    
    @staticmethod
    def validate_cnpj(cnpj):
        """Valida CNPJ (algoritmo básico)"""
        if not cnpj:
            return False
        
        # Remove caracteres não numéricos
        cnpj = re.sub(r'\D', '', cnpj)
        
        # Verifica se tem 14 dígitos
        if len(cnpj) != 14:
            return False
        
        # Verifica sequências inválidas
        if cnpj == cnpj[0] * 14:
            return False
        
        return True  # Implementação simplificada
    
    @staticmethod
    def format_cnpj(cnpj):
        """Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX"""
        if not cnpj:
            return ""
        
        cnpj = re.sub(r'\D', '', cnpj)
        
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        
        return cnpj

class StatusUtils:
    """Utilitários para formatação de status"""
    
    STATUS_COLORS = {
        'Operacional': 'success',
        'Manutenção': 'warning',
        'Inativo': 'danger',
        'Agendada': 'warning',
        'Em Andamento': 'info',
        'Concluída': 'success',
        'Cancelada': 'danger',
        'Preventiva': 'info',
        'Corretiva': 'warning',
        'Emergencial': 'danger',
        'Revisão': 'primary'
    }
    
    @staticmethod
    def get_status_color(status):
        """Retorna a classe CSS de cor para um status"""
        return StatusUtils.STATUS_COLORS.get(status, 'secondary')
    
    @staticmethod
    def get_status_icon(status):
        """Retorna o ícone Font Awesome para um status"""
        icons = {
            'Operacional': 'fas fa-check-circle',
            'Manutenção': 'fas fa-wrench',
            'Inativo': 'fas fa-times-circle',
            'Agendada': 'fas fa-clock',
            'Em Andamento': 'fas fa-cog fa-spin',
            'Concluída': 'fas fa-check',
            'Cancelada': 'fas fa-ban',
            'Preventiva': 'fas fa-shield-alt',
            'Corretiva': 'fas fa-tools',
            'Emergencial': 'fas fa-exclamation-triangle',
            'Revisão': 'fas fa-search'
        }
        return icons.get(status, 'fas fa-question')

class FileUtils:
    """Utilitários para manipulação de arquivos"""
    
    @staticmethod
    def ensure_directory(path):
        """Garante que um diretório existe"""
        os.makedirs(path, exist_ok=True)
    
    @staticmethod
    def get_safe_filename(filename):
        """Retorna um nome de arquivo seguro"""
        # Remove caracteres problemáticos
        safe_chars = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove espaços extras e pontos no final
        safe_chars = re.sub(r'\s+', '_', safe_chars).strip('._')
        
        return safe_chars or 'arquivo'
    
    @staticmethod
    def get_file_size_mb(file_path):
        """Retorna o tamanho do arquivo em MB"""
        try:
            size_bytes = os.path.getsize(file_path)
            return round(size_bytes / (1024 * 1024), 2)
        except OSError:
            return None

class AlertUtils:
    """Utilitários para alertas e notificações"""
    
    @staticmethod
    def get_maintenance_alerts(manutencoes, days_ahead=7):
        """Retorna alertas de manutenções próximas"""
        alerts = []
        today = date.today()
        
        for manutencao in manutencoes:
            if manutencao.get('status') != 'Agendada':
                continue
            
            data_agendada = manutencao.get('data_agendada')
            if not data_agendada:
                continue
            
            if isinstance(data_agendada, str):
                try:
                    data_agendada = datetime.strptime(data_agendada, "%Y-%m-%d").date()
                except ValueError:
                    continue
            
            days_until = (data_agendada - today).days
            
            if days_until <= days_ahead:
                alert_type = 'danger' if days_until <= 1 else 'warning' if days_until <= 3 else 'info'
                
                alerts.append({
                    'type': alert_type,
                    'message': f"Manutenção {manutencao.get('tipo', '')} do veículo {manutencao.get('veiculo_placa', '')} " +
                              f"em {days_until} dia(s)",
                    'days_until': days_until,
                    'manutencao_id': manutencao.get('id')
                })
        
        return sorted(alerts, key=lambda x: x['days_until'])
    
    @staticmethod
    def get_stock_alerts(pecas, threshold_multiplier=1.5):
        """Retorna alertas de estoque baixo"""
        alerts = []
        
        for peca in pecas:
            estoque_atual = peca.get('quantidade_estoque', 0)
            estoque_minimo = peca.get('estoque_minimo', 5)
            threshold = int(estoque_minimo * threshold_multiplier)
            
            if estoque_atual <= estoque_minimo:
                alert_type = 'danger'
                message = f"Estoque CRÍTICO: {peca.get('nome', '')} ({estoque_atual} unidades)"
            elif estoque_atual <= threshold:
                alert_type = 'warning'
                message = f"Estoque BAIXO: {peca.get('nome', '')} ({estoque_atual} unidades)"
            else:
                continue
            
            alerts.append({
                'type': alert_type,
                'message': message,
                'estoque_atual': estoque_atual,
                'estoque_minimo': estoque_minimo,
                'peca_id': peca.get('id')
            })
        
        return sorted(alerts, key=lambda x: x['estoque_atual'])

# Funções de conveniência para templates Jinja2
def register_template_utils(app):
    """Registra utilitários como filtros do Jinja2"""
    
    app.jinja_env.filters['format_date_br'] = DateUtils.format_date_br
    app.jinja_env.filters['format_datetime_br'] = DateUtils.format_datetime_br
    app.jinja_env.filters['format_currency'] = CurrencyUtils.format_currency
    app.jinja_env.filters['format_placa'] = ValidationUtils.format_placa
    app.jinja_env.filters['format_cnpj'] = ValidationUtils.format_cnpj
    app.jinja_env.filters['status_color'] = StatusUtils.get_status_color
    app.jinja_env.filters['status_icon'] = StatusUtils.get_status_icon
    
    # Funções globais para templates
    app.jinja_env.globals['days_until'] = DateUtils.days_until