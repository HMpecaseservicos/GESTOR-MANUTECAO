"""
Módulo de Relatórios - Sistema de Gestão de Manutenção
=====================================================

Este módulo gera relatórios em PDF para o sistema.
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
import os

class ReportGenerator:
    """Gerador de relatórios em PDF"""
    
    def __init__(self, reports_folder='reports'):
        self.reports_folder = reports_folder
        os.makedirs(reports_folder, exist_ok=True)
        self.styles = getSampleStyleSheet()
    
    def generate_maintenance_report(self, manutencoes, filename=None):
        """Gera relatório de manutenções em PDF"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_manutencoes_{timestamp}.pdf"
        
        filepath = os.path.join(self.reports_folder, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Centralizado
        )
        
        title = Paragraph("Relatório de Manutenções", title_style)
        elements.append(title)
        
        # Data do relatório
        date_p = Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          self.styles['Normal'])
        elements.append(date_p)
        elements.append(Spacer(1, 20))
        
        # Tabela de dados
        if manutencoes:
            headers = ['ID', 'Veículo', 'Tipo', 'Data Agendada', 'Status', 'Custo']
            data = [headers]
            
            for m in manutencoes:
                row = [
                    str(m.get('id', '')),
                    f"{m.get('placa', '')} - {m.get('modelo', '')}",
                    m.get('tipo', ''),
                    m.get('data_agendada', ''),
                    m.get('status', ''),
                    f"R$ {m.get('custo_total', 0):.2f}"
                ]
                data.append(row)
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("Nenhuma manutenção encontrada.", self.styles['Normal']))
        
        doc.build(elements)
        return filepath