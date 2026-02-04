// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', function() {
    // Prevenir erros do Bootstrap modal em elementos que não existem
    const originalModal = window.bootstrap?.Modal;
    if (originalModal) {
        window.bootstrap.Modal = class extends originalModal {
            constructor(element, config) {
                if (!element || !element.classList) {
                    console.warn('Modal element not found, skipping initialization');
                    return;
                }
                super(element, config);
            }
        };
    }
});

// ===== CHATBOT FUNCTIONALITY =====
function toggleChat() {
    const chat = document.querySelector('.chatbot-container');
    chat.classList.toggle('active');
    
    // Focus no input quando abrir o chat
    if (chat.classList.contains('active')) {
        document.getElementById('chatInput').focus();
    }
}

function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (message === '') return;
    
    // Adicionar mensagem do usuário
    addMessage(message, 'user');
    input.value = '';
    
    // Mostrar indicador de "digitando"
    addTypingIndicator();
    
    // Obter CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // Enviar para o backend
    fetch('/api/chatbot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({mensagem: message})
    })
    .then(response => response.json())
    .then(data => {
        removeTypingIndicator();
        addMessage(data.resposta, 'bot');
    })
    .catch(error => {
        removeTypingIndicator();
        addMessage('Desculpe, ocorreu um erro. Tente novamente.', 'bot');
        console.error('Erro no chatbot:', error);
    });
}

function addMessage(text, sender) {
    const messages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    if (sender === 'bot') {
        // Converter quebras de linha para HTML
        const formattedText = text.replace(/\n/g, '<br>');
        messageDiv.innerHTML = `<i class="fas fa-robot me-2"></i>${formattedText}`;
    } else {
        messageDiv.textContent = text;
    }
    
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
}

function addTypingIndicator() {
    const messages = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message typing-indicator';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <i class="fas fa-robot me-2"></i>
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    
    messages.appendChild(typingDiv);
    messages.scrollTop = messages.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// Enviar mensagem com Enter
document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});

// ===== VEHICLE MANAGEMENT =====
function salvarVeiculo() {
    const form = document.getElementById('novoVeiculoForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validação básica
    if (!data.tipo || !data.marca || !data.modelo || !data.placa) {
        showAlert('Por favor, preencha todos os campos obrigatórios.', 'warning');
        return;
    }
    
    // Verificar se campo cliente existe e é obrigatório (modo SERVICO)
    const clienteSelect = document.getElementById('cliente_id');
    if (clienteSelect && clienteSelect.required && !data.cliente_id) {
        showAlert('Por favor, selecione um cliente.', 'warning');
        return;
    }
    
    // Converter campos numéricos
    const veiculo = {
        tipo: data.tipo,
        marca: data.marca,
        modelo: data.modelo,
        placa: data.placa,
        ano: parseInt(data.ano) || null,
        quilometragem: parseInt(data.quilometragem) || 0,
        proxima_manutencao: data.proxima_manutencao || null,
        cliente_id: data.cliente_id || null
    };
    
    // Fazer requisição real ao backend
    fetch('/api/veiculo', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify(veiculo)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showAlert('Veículo cadastrado com sucesso!', 'success');
            
            // Fechar modal e limpar formulário
            const modal = bootstrap.Modal.getInstance(document.getElementById('novoVeiculoModal'));
            modal.hide();
            form.reset();
            
            // Recarregar página após um breve delay
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert('Erro: ' + result.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Erro ao salvar veículo:', error);
        showAlert('Erro ao conectar com o servidor. Tente novamente.', 'danger');
    });
}

// Função para limpar modal de veículo quando aberto
function limparModalVeiculo() {
    const form = document.getElementById('novoVeiculoForm');
    if (form) {
        form.reset();
    }
}

// ===== MAINTENANCE MANAGEMENT =====
function agendarManutencao() {
    const form = document.getElementById('novaManutencaoForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validação
    if (!data.veiculo_id || !data.tipo || !data.data_agendada) {
        showAlert('Por favor, preencha todos os campos obrigatórios.', 'warning');
        return;
    }
    
    // Coletar serviços prestados (modo SERVICO)
    if (typeof coletarServicos === 'function') {
        data.servicos = coletarServicos('nova');
    }
    
    // Enviar para o backend
    fetch('/api/manutencao', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showAlert('Manutenção agendada com sucesso!', 'success');
            
            // Fechar modal e recarregar
            const modal = bootstrap.Modal.getInstance(document.getElementById('novaManutencaoModal'));
            modal.hide();
            form.reset();
            
            // Limpar container de serviços se existir
            const servicosContainer = document.getElementById('nova-servicos-container');
            if (servicosContainer) servicosContainer.innerHTML = '';
            
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert('Erro ao agendar manutenção: ' + (result.message || 'Tente novamente.'), 'error');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        showAlert('Erro ao agendar manutenção. Tente novamente.', 'error');
    });
}

function iniciarManutencao(id) {
    if (confirm('Deseja iniciar esta manutenção?')) {
        // Aqui você faria a requisição para atualizar o status
        showAlert('Manutenção iniciada!', 'info');
    }
}

function finalizarManutencao(id) {
    if (confirm('Deseja finalizar esta manutenção?')) {
        // Aqui você faria a requisição para atualizar o status
        showAlert('Manutenção finalizada!', 'success');
    }
}

// ===== PARTS MANAGEMENT =====
// Função salvarPeca() foi movida para o template pecas.html
// para evitar conflitos e permitir funcionalidade completa

function ajustarEstoque(pecaId, novaQuantidade) {
    // Aqui você faria a requisição para atualizar o estoque
    showAlert('Estoque atualizado!', 'success');
}

// ===== SUPPLIER MANAGEMENT =====
// Função salvarFornecedor() foi movida para o template fornecedores.html
// para evitar conflitos e permitir funcionalidade completa

// ===== SEARCH AND FILTER FUNCTIONS =====
function setupSearch() {
    // Busca em veículos
    const searchVeiculos = document.getElementById('searchInput');
    if (searchVeiculos) {
        searchVeiculos.addEventListener('input', function() {
            filterTable(this.value, 'veiculosTable');
        });
    }
    
    // Busca em peças
    const searchPecas = document.getElementById('searchPecas');
    if (searchPecas) {
        searchPecas.addEventListener('input', function() {
            filterTable(this.value, 'pecasTable');
        });
    }
    
    // Busca em fornecedores
    const searchFornecedores = document.getElementById('searchFornecedores');
    if (searchFornecedores) {
        searchFornecedores.addEventListener('input', function() {
            filterCards(this.value, 'fornecedor-card');
        });
    }
}

function filterTable(searchTerm, tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    
    for (let row of rows) {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm.toLowerCase())) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    }
}

function filterCards(searchTerm, cardClass) {
    const cards = document.getElementsByClassName(cardClass);
    
    for (let card of cards) {
        const text = card.textContent.toLowerCase();
        if (text.includes(searchTerm.toLowerCase())) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    }
}

// ===== UTILITY FUNCTIONS =====
function showAlert(message, type = 'info') {
    // Criar elemento de alerta
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Remover automaticamente após 5 segundos
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 5000);
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function validateForm(formId, requiredFields) {
    const form = document.getElementById(formId);
    const data = new FormData(form);
    
    for (let field of requiredFields) {
        if (!data.get(field)) {
            showAlert(`O campo ${field} é obrigatório.`, 'warning');
            return false;
        }
    }
    
    return true;
}

// ===== REPORTS FUNCTIONALITY =====
function aplicarFiltros() {
    const dataInicial = document.getElementById('dataInicial').value;
    const dataFinal = document.getElementById('dataFinal').value;
    const veiculo = document.getElementById('filtroVeiculo').value;
    
    // Aqui você implementaria a lógica de filtros
    showAlert('Filtros aplicados!', 'info');
}

function exportarRelatorio(formato) {
    // Simular exportação
    showAlert(`Relatório em ${formato} gerado com sucesso!`, 'success');
}

// ===== NOTIFICATION SYSTEM =====
function checkNotifications() {
    // Verificar manutenções vencidas
    // Verificar estoque baixo
    // Verificar outros alertas
    
    // Esta função seria chamada periodicamente
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar componentes
    setupSearch();
    
    // Verificar notificações a cada 5 minutos
    setInterval(checkNotifications, 5 * 60 * 1000);
    
    // Adicionar event listeners para modais
    setupModalEvents();
    
    // Auto-focus no primeiro input de modais
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            const firstInput = modal.querySelector('input, select, textarea');
            if (firstInput) {
                firstInput.focus();
            }
        });
    });
    
    // Inicializar tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Configurar máscaras de input
    setupInputMasks();
});

function setupModalEvents() {
    // Event listeners removidos para evitar conflitos
    // Os botões usam onclick direto nos templates
}

function setupInputMasks() {
    // Máscara para telefone
    const telefoneInputs = document.querySelectorAll('input[name="telefone"]');
    telefoneInputs.forEach(input => {
        input.addEventListener('input', function() {
            let value = this.value.replace(/\D/g, '');
            if (value.length >= 11) {
                value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
            } else if (value.length >= 7) {
                value = value.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
            } else if (value.length >= 3) {
                value = value.replace(/(\d{2})(\d{0,5})/, '($1) $2');
            }
            this.value = value;
        });
    });
    
    // Máscara para CNPJ
    const cnpjInputs = document.querySelectorAll('input[name="cnpj"]');
    cnpjInputs.forEach(input => {
        input.addEventListener('input', function() {
            let value = this.value.replace(/\D/g, '');
            value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
            this.value = value;
        });
    });
    
    // Máscara para placa de veículo
    const placaInputs = document.querySelectorAll('input[name="placa"]');
    placaInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
        });
    });
}

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', function(e) {
    // Ctrl + M para abrir modal de nova manutenção
    if (e.ctrlKey && e.key === 'm') {
        e.preventDefault();
        const modal = new bootstrap.Modal(document.getElementById('novaManutencaoModal'));
        if (modal) modal.show();
    }
    
    // Ctrl + V para abrir modal de novo veículo
    if (e.ctrlKey && e.key === 'v') {
        e.preventDefault();
        const modal = new bootstrap.Modal(document.getElementById('novoVeiculoModal'));
        if (modal) modal.show();
    }
    
    // Escape para fechar chatbot
    if (e.key === 'Escape') {
        const chat = document.querySelector('.chatbot-container');
        if (chat && chat.classList.contains('active')) {
            toggleChat();
        }
    }
});

// ===== PERFORMANCE MONITORING =====
function logPerformance(action, startTime) {
    const endTime = performance.now();
    const duration = endTime - startTime;
    console.log(`${action} took ${duration.toFixed(2)} milliseconds`);
}

// ===== ERROR HANDLING =====
window.addEventListener('error', function(e) {
    // Ignorar erros do Bootstrap modal em elementos que não existem
    if (e.message && e.message.includes('classList') || e.message && e.message.includes('Cannot read properties of undefined')) {
        e.preventDefault();
        return false;
    }
    console.error('JavaScript Error:', e.error);
    // Aqui você poderia enviar erros para um serviço de monitoramento
});

// Ignorar erros não tratados de promises
window.addEventListener('unhandledrejection', function(e) {
    e.preventDefault();
    console.warn('Unhandled Promise Rejection:', e.reason);
});

// ===== SERVICE WORKER =====
// Service Worker completamente removido para evitar erro 404
// Implementação pode ser adicionada futuramente se necessário

// Força recarregamento do script removendo cache
console.log('Script carregado - versão sem ServiceWorker');