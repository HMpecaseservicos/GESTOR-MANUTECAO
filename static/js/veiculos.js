/**
 * Módulo de Frota/Veículos - GESTOR-MANUTENCAO
 * Gerencia CRUD de veículos/equipamentos com busca, filtros e categorias
 */

(function() {
    'use strict';

    // ==========================================
    // ESTADO GLOBAL
    // ==========================================
    let categoriasData = [];
    let iconeSelecionado = 'fa-truck';
    let corSelecionada = 'primary';

    // ==========================================
    // INICIALIZAÇÃO
    // ==========================================
    
    document.addEventListener('DOMContentLoaded', function() {
        inicializarEventos();
        inicializarBuscaFiltros();
    });

    function inicializarEventos() {
        // Limpar modal de novo veículo quando aberto
        const modalNovo = document.getElementById('novoVeiculoModal');
        if (modalNovo) {
            modalNovo.addEventListener('show.bs.modal', function() {
                const form = document.getElementById('novoVeiculoForm');
                if (form) form.reset();
            });
        }

        // Carregar categorias ao abrir modal de gerenciamento
        const modalCategorias = document.getElementById('gerenciarCategoriasModal');
        if (modalCategorias) {
            modalCategorias.addEventListener('show.bs.modal', carregarCategorias);
        }
    }

    // ==========================================
    // BUSCA E FILTROS
    // ==========================================

    function inicializarBuscaFiltros() {
        const searchInput = document.getElementById('searchInput');
        const filterStatus = document.getElementById('filterStatus');
        const filterTipo = document.getElementById('filterTipo');
        const filterCliente = document.getElementById('filterCliente');

        if (searchInput) {
            searchInput.addEventListener('input', debounce(aplicarFiltros, 300));
        }
        if (filterStatus) {
            filterStatus.addEventListener('change', aplicarFiltros);
        }
        if (filterTipo) {
            filterTipo.addEventListener('change', aplicarFiltros);
        }
        if (filterCliente) {
            filterCliente.addEventListener('change', aplicarFiltros);
        }
    }

    function aplicarFiltros() {
        const searchTerm = (document.getElementById('searchInput')?.value || '').toLowerCase().trim();
        const statusFiltro = document.getElementById('filterStatus')?.value || '';
        const tipoFiltro = document.getElementById('filterTipo')?.value || '';
        const clienteFiltro = document.getElementById('filterCliente')?.value || '';

        const cards = document.querySelectorAll('.veiculo-card');
        let visiveis = 0;

        cards.forEach(card => {
            const texto = card.textContent.toLowerCase();
            const status = card.getAttribute('data-status') || '';
            const tipo = card.getAttribute('data-tipo') || '';
            const clienteId = card.getAttribute('data-cliente') || '';

            const matchTexto = !searchTerm || texto.includes(searchTerm);
            const matchStatus = !statusFiltro || status === statusFiltro;
            const matchTipo = !tipoFiltro || tipo.toLowerCase().includes(tipoFiltro.toLowerCase());
            const matchCliente = !clienteFiltro || clienteId === clienteFiltro;

            if (matchTexto && matchStatus && matchTipo && matchCliente) {
                card.style.display = '';
                visiveis++;
            } else {
                card.style.display = 'none';
            }
        });

        atualizarContadorFiltros(visiveis, cards.length);
    }

    function atualizarContadorFiltros(visiveis, total) {
        let contador = document.getElementById('contadorResultados');
        
        if (!contador) {
            const containerFiltros = document.querySelector('.filtros-container');
            if (containerFiltros) {
                contador = document.createElement('small');
                contador.id = 'contadorResultados';
                contador.className = 'text-muted ms-3';
                containerFiltros.appendChild(contador);
            }
        }

        if (contador) {
            if (visiveis === total) {
                contador.textContent = '';
            } else {
                contador.textContent = `Exibindo ${visiveis} de ${total}`;
            }
        }
    }

    function limparFiltros() {
        const searchInput = document.getElementById('searchInput');
        const filterStatus = document.getElementById('filterStatus');
        const filterTipo = document.getElementById('filterTipo');
        const filterCliente = document.getElementById('filterCliente');

        if (searchInput) searchInput.value = '';
        if (filterStatus) filterStatus.value = '';
        if (filterTipo) filterTipo.value = '';
        if (filterCliente) filterCliente.value = '';

        aplicarFiltros();
    }

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // ==========================================
    // CRUD - EDITAR VEÍCULO
    // ==========================================

    function editarVeiculo(veiculoId) {
        fetch(`/api/veiculo/${veiculoId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const veiculo = data.veiculo;
                    
                    document.getElementById('edit-veiculo-id').value = veiculo.id;
                    document.getElementById('edit-tipo').value = veiculo.tipo || '';
                    document.getElementById('edit-marca').value = veiculo.marca || '';
                    document.getElementById('edit-modelo').value = veiculo.modelo || '';
                    document.getElementById('edit-placa').value = veiculo.placa || '';
                    document.getElementById('edit-ano').value = veiculo.ano || '';
                    document.getElementById('edit-quilometragem').value = veiculo.quilometragem || '';
                    document.getElementById('edit-proxima-manutencao').value = veiculo.proxima_manutencao || '';
                    
                    // Carregar unidade de medida
                    const unidadeSelect = document.getElementById('edit-unidade-medida');
                    if (unidadeSelect) {
                        unidadeSelect.value = veiculo.unidade_medida || 'km';
                    }
                    
                    const clienteSelect = document.getElementById('edit-cliente-id');
                    if (clienteSelect) {
                        clienteSelect.value = veiculo.cliente_id || '';
                    }
                    
                    const modal = new bootstrap.Modal(document.getElementById('editarVeiculoModal'));
                    modal.show();
                } else {
                    alert('Erro ao carregar dados: ' + data.message);
                }
            })
            .catch(() => {
                alert('Erro ao carregar dados do veículo');
            });
    }

    function salvarEdicaoVeiculo() {
        const veiculoId = document.getElementById('edit-veiculo-id').value;
        const clienteSelect = document.getElementById('edit-cliente-id');
        const clienteId = clienteSelect ? clienteSelect.value : null;
        
        if (clienteSelect && clienteSelect.required && !clienteId) {
            alert('Por favor, selecione um cliente.');
            return;
        }
        
        const dados = {
            tipo: document.getElementById('edit-tipo').value,
            marca: document.getElementById('edit-marca').value,
            modelo: document.getElementById('edit-modelo').value,
            placa: document.getElementById('edit-placa').value,
            ano: parseInt(document.getElementById('edit-ano').value) || null,
            quilometragem: parseInt(document.getElementById('edit-quilometragem').value) || 0,
            unidade_medida: document.getElementById('edit-unidade-medida')?.value || 'km',
            proxima_manutencao: document.getElementById('edit-proxima-manutencao').value || null,
            cliente_id: clienteId || null
        };
        
        if (!dados.tipo || !dados.marca || !dados.modelo || !dados.placa) {
            alert('Por favor, preencha todos os campos obrigatórios.');
            return;
        }
        
        fetch(`/api/veiculo/${veiculoId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert('Veículo atualizado com sucesso!');
                const modal = bootstrap.Modal.getInstance(document.getElementById('editarVeiculoModal'));
                modal.hide();
                setTimeout(() => location.reload(), 1000);
            } else {
                alert('Erro: ' + result.message);
            }
        })
        .catch(() => {
            alert('Erro ao salvar alterações');
        });
    }

    // ==========================================
    // CRUD - EXCLUIR VEÍCULO
    // ==========================================

    function excluirVeiculo(id, descricao) {
        if (!confirm(`Tem certeza que deseja excluir:\n${descricao}?`)) return;
        
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        fetch(`/api/veiculo/${id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            if (data.success) location.reload();
        })
        .catch(() => {
            alert('Erro ao excluir veículo!');
        });
    }

    // ==========================================
    // AJUSTE DE QUILOMETRAGEM/HORAS
    // ==========================================

    function ajustarCampoQuilometragem(modalType) {
        const tipoSelect = document.getElementById(modalType === 'novo' ? 'tipo' : 'edit-tipo');
        const unidadeSelect = document.getElementById(modalType === 'novo' ? 'unidade-quilometragem-novo' : 'edit-unidade-medida');
        
        if (tipoSelect && unidadeSelect) {
            const tipoSelecionado = tipoSelect.value.toLowerCase();
            
            // Tipos que usam horas em vez de km
            const tiposHoras = ['máquina', 'maquina', 'equipamento', 'gerador', 'compressor', 
                                'prensa', 'bomba', 'empilhadeira', 'guincho', 'implemento', 'ferramenta'];
            
            const usaHoras = tiposHoras.some(t => tipoSelecionado.includes(t));
            unidadeSelect.value = usaHoras ? 'hr' : 'km';
        }
    }

    // ==========================================
    // GERENCIAMENTO DE CATEGORIAS
    // ==========================================

    function carregarCategorias() {
        fetch('/api/categorias-veiculos')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    categoriasData = data.categorias;
                    renderizarCategorias();
                }
            });
    }

    function renderizarCategorias() {
        const veiculosContainer = document.getElementById('lista-veiculos-categorias');
        const equipamentosContainer = document.getElementById('lista-equipamentos-categorias');
        
        if (!veiculosContainer || !equipamentosContainer) return;
        
        const veiculos = categoriasData.filter(c => c.grupo === 'Veículo');
        const equipamentos = categoriasData.filter(c => c.grupo === 'Equipamento');
        
        document.getElementById('count-veiculos').textContent = veiculos.length;
        document.getElementById('count-equipamentos').textContent = equipamentos.length;
        
        const btnInicializar = document.getElementById('btn-inicializar-container');
        if (btnInicializar) {
            btnInicializar.style.display = categoriasData.length === 0 ? 'block' : 'none';
        }
        
        veiculosContainer.innerHTML = veiculos.length === 0 
            ? '<p class="text-muted text-center py-4">Nenhuma categoria de veículo</p>'
            : veiculos.map(cat => gerarCardCategoria(cat)).join('');
        
        equipamentosContainer.innerHTML = equipamentos.length === 0 
            ? '<p class="text-muted text-center py-4">Nenhuma categoria de equipamento</p>'
            : equipamentos.map(cat => gerarCardCategoria(cat)).join('');
    }

    function gerarCardCategoria(cat) {
        return `
            <div class="card mb-2 shadow-sm categoria-card" data-id="${cat.id}">
                <div class="card-body py-2 px-3">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="d-flex align-items-center">
                            <div class="rounded-circle bg-${cat.cor} d-flex align-items-center justify-content-center me-3" 
                                 style="width: 45px; height: 45px;">
                                <i class="fas ${cat.icone} text-white"></i>
                            </div>
                            <div>
                                <h6 class="mb-0">${cat.nome}</h6>
                                <small class="text-muted">${cat.grupo}</small>
                            </div>
                        </div>
                        <div class="btn-group">
                            <button class="btn btn-sm btn-outline-primary" onclick="abrirEditarCategoria(${cat.id})" title="Editar">
                                <i class="fas fa-pen"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="excluirCategoria(${cat.id}, '${cat.nome}')" title="Excluir">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function inicializarCategoriasPadrao() {
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
        fetch('/api/categorias-veiculos/inicializar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(r => r.json())
        .then(data => {
            alert(data.message);
            if (data.success) carregarCategorias();
        });
    }

    function excluirCategoria(id, nome) {
        if (!confirm(`Excluir categoria "${nome}"?`)) return;
        
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
        fetch(`/api/categorias-veiculos/${id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(r => r.json())
        .then(data => {
            alert(data.message);
            if (data.success) carregarCategorias();
        });
    }

    function abrirEditarCategoria(id) {
        const cat = categoriasData.find(c => c.id === id);
        if (!cat) return;
        
        const novoNome = prompt('Nome da categoria:', cat.nome);
        if (novoNome && novoNome !== cat.nome) {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            fetch(`/api/categorias-veiculos/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ ...cat, nome: novoNome })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                if (data.success) carregarCategorias();
            });
        }
    }

    function salvarNovaCategoria() {
        const nome = document.getElementById('cat-nome').value.trim();
        const grupo = document.querySelector('input[name="cat-grupo-radio"]:checked')?.value || 'Veículo';
        
        if (!nome) {
            alert('Digite o nome da categoria!');
            return;
        }
        
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
        fetch('/api/categorias-veiculos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ 
                nome, 
                icone: iconeSelecionado, 
                cor: corSelecionada, 
                grupo 
            })
        })
        .then(r => r.json())
        .then(data => {
            alert(data.message);
            if (data.success) {
                document.getElementById('cat-nome').value = '';
                carregarCategorias();
            }
        });
    }

    // ==========================================
    // PREVIEW DE CATEGORIA
    // ==========================================

    function selecionarIcone(btn) {
        document.querySelectorAll('.icone-btn').forEach(b => {
            b.classList.remove('active', 'btn-primary');
            b.classList.add('btn-outline-secondary');
        });
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('active', 'btn-primary');
        iconeSelecionado = btn.dataset.icone;
        atualizarPreview();
    }

    function selecionarCor(btn) {
        document.querySelectorAll('.cor-btn').forEach(b => b.style.border = '3px solid transparent');
        btn.style.border = '3px solid #000';
        corSelecionada = btn.dataset.cor;
        atualizarPreview();
    }

    function atualizarPreview() {
        const nome = document.getElementById('cat-nome')?.value || 'Nova Categoria';
        const grupo = document.querySelector('input[name="cat-grupo-radio"]:checked')?.value || 'Veículo';
        
        const previewNome = document.getElementById('preview-nome');
        const previewGrupo = document.getElementById('preview-grupo');
        const previewIcone = document.getElementById('preview-icone');
        
        if (previewNome) previewNome.textContent = nome;
        if (previewGrupo) previewGrupo.textContent = grupo;
        if (previewIcone) previewIcone.className = `fas ${iconeSelecionado} fa-2x text-white`;
        
        const gradientes = {
            'primary': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'success': 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
            'info': 'linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%)',
            'warning': 'linear-gradient(135deg, #f2994a 0%, #f2c94c 100%)',
            'danger': 'linear-gradient(135deg, #eb3349 0%, #f45c43 100%)',
            'secondary': 'linear-gradient(135deg, #3a7bd5 0%, #00d2ff 100%)',
            'dark': 'linear-gradient(135deg, #232526 0%, #414345 100%)'
        };
        
        const previewContainer = document.querySelector('.p-4.rounded-3');
        if (previewContainer) {
            previewContainer.style.background = gradientes[corSelecionada] || gradientes.primary;
        }
    }

    // ==========================================
    // EXPORTAR FUNÇÕES GLOBAIS
    // ==========================================
    
    window.editarVeiculo = editarVeiculo;
    window.salvarEdicaoVeiculo = salvarEdicaoVeiculo;
    window.excluirVeiculo = excluirVeiculo;
    window.ajustarCampoQuilometragem = ajustarCampoQuilometragem;
    window.carregarCategorias = carregarCategorias;
    window.inicializarCategoriasPadrao = inicializarCategoriasPadrao;
    window.excluirCategoria = excluirCategoria;
    window.abrirEditarCategoria = abrirEditarCategoria;
    window.salvarNovaCategoria = salvarNovaCategoria;
    window.selecionarIcone = selecionarIcone;
    window.selecionarCor = selecionarCor;
    window.atualizarPreview = atualizarPreview;
    window.limparFiltros = limparFiltros;
    window.aplicarFiltros = aplicarFiltros;

})();
