/**
 * 3D Print Calc Pro - Main Application Controller
 */

const state = {
    user: null,
    printers: [],
    filaments: [],
    projects: [],
    currentProject: null,
    currentPlates: [],
    currentBOM: [],
    activeView: 'dashboard',
};

// ================= UTILITIES & HELPERS =================

function formatCurrency(val) {
    const num = Number(val) || 0;
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const colors = {
        success: 'bg-emerald-600 text-white border-emerald-500',
        error: 'bg-red-600 text-white border-red-500',
        info: 'bg-blue-600 text-white border-blue-500',
    };

    const toast = document.createElement('div');
    toast.className = `p-3 rounded-lg border shadow-lg text-xs font-semibold flex items-center gap-2 pointer-events-auto transition-all transform duration-300 translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

// ================= NAVIGATION =================

function navigateTo(viewName) {
    state.activeView = viewName;

    const views = ['dashboard', 'projects', 'project-editor', 'printers', 'filaments', 'settings'];
    views.forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) el.classList.add('hidden');

        const navBtn = document.getElementById(`nav-${v}`);
        if (navBtn) {
            navBtn.classList.remove('bg-blue-600', 'text-white');
            navBtn.classList.add('text-slate-300');
        }
    });

    const activeEl = document.getElementById(`view-${viewName}`);
    if (activeEl) activeEl.classList.remove('hidden');

    const activeNav = document.getElementById(`nav-${viewName}`);
    if (activeNav) {
        activeNav.classList.remove('text-slate-300');
        activeNav.classList.add('bg-blue-600', 'text-white');
    }

    const titles = {
        'dashboard': 'Visão Geral',
        'projects': 'Projetos & Orçamentos',
        'project-editor': 'Editar Orçamento',
        'printers': 'Minhas Impressoras',
        'filaments': 'Meus Filamentos',
        'settings': 'Configurações & Taxas',
    };
    const titleEl = document.getElementById('view-title');
    if (titleEl) titleEl.textContent = titles[viewName] || 'Painel';

    // Reload views if needed
    if (viewName === 'dashboard') loadDashboard();
    if (viewName === 'projects') renderProjectsTable();
    if (viewName === 'printers') renderPrintersGrid();
    if (viewName === 'filaments') renderFilamentsGrid();
    if (viewName === 'settings') populateSettingsForm();

    refreshIcons();
}

// ================= AUTH FLOWS =================

function switchAuthTab(tab) {
    const loginForm = document.getElementById('form-login');
    const regForm = document.getElementById('form-register');
    const loginBtn = document.getElementById('tab-login-btn');
    const regBtn = document.getElementById('tab-register-btn');

    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        regForm.classList.add('hidden');
        loginBtn.classList.add('border-blue-500', 'text-blue-400');
        loginBtn.classList.remove('border-transparent', 'text-slate-400');
        regBtn.classList.remove('border-blue-500', 'text-blue-400');
        regBtn.classList.add('border-transparent', 'text-slate-400');
    } else {
        loginForm.classList.add('hidden');
        regForm.classList.remove('hidden');
        regBtn.classList.add('border-blue-500', 'text-blue-400');
        regBtn.classList.remove('border-transparent', 'text-slate-400');
        loginBtn.classList.remove('border-blue-500', 'text-blue-400');
        loginBtn.classList.add('border-transparent', 'text-slate-400');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const res = await API.auth.login(email, password);
        state.user = res.user;
        document.getElementById('auth-modal').classList.add('hidden');
        showToast('Login realizado com sucesso!', 'success');
        updateUserUI();
        await loadAllData();
        navigateTo('dashboard');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const company = document.getElementById('reg-company').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;

    try {
        const res = await API.auth.register(email, password, name, company);
        state.user = res.user;
        document.getElementById('auth-modal').classList.add('hidden');
        showToast('Conta criada com sucesso! Sua conta inicia 100% limpa.', 'success');
        updateUserUI();
        await loadAllData();
        navigateTo('dashboard');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function updateUserUI() {
    if (!state.user) return;
    const nameEl = document.getElementById('user-display-name');
    const compEl = document.getElementById('user-display-company');
    const avatarEl = document.getElementById('user-avatar');

    const displayName = state.user.full_name || state.user.email.split('@')[0];
    if (nameEl) nameEl.textContent = displayName;
    if (compEl) compEl.textContent = state.user.company_name || 'Profissional Autônomo';
    if (avatarEl) avatarEl.textContent = displayName.charAt(0).toUpperCase();
}

// ================= DATA LOADING =================

async function loadAllData() {
    try {
        const [printers, filaments, projects] = await Promise.all([
            API.printers.list(),
            API.filaments.list(),
            API.projects.list(),
        ]);
        state.printers = printers || [];
        state.filaments = filaments || [];
        state.projects = projects || [];
    } catch (err) {
        console.error("Erro carregando dados:", err);
    }
}

async function loadDashboard() {
    await loadAllData();

    // Stats
    document.getElementById('stat-projects-count').textContent = state.projects.length;
    document.getElementById('stat-printers-count').textContent = state.printers.length;
    document.getElementById('stat-filaments-count').textContent = state.filaments.length;

    const activeQuotes = state.projects.filter(p => ['draft', 'quoted', 'in_production'].includes(p.status)).length;
    document.getElementById('stat-active-quotes').textContent = activeQuotes;

    // Empty account onboarding notice
    const emptyBanner = document.getElementById('dashboard-empty-banner');
    if (state.printers.length === 0 && state.filaments.length === 0 && state.projects.length === 0) {
        emptyBanner.classList.remove('hidden');
    } else {
        emptyBanner.classList.add('hidden');
    }

    // Recent projects
    const recentContainer = document.getElementById('dashboard-recent-projects');
    if (!recentContainer) return;

    if (state.projects.length === 0) {
        recentContainer.innerHTML = `
            <div class="text-center py-8 text-slate-400">
                <i data-lucide="inbox" class="w-10 h-10 mx-auto mb-2 text-slate-600"></i>
                <p class="text-sm">Nenhum orçamento cadastrado ainda.</p>
                <button onclick="openNewProject()" class="mt-3 text-xs font-semibold text-blue-400 hover:underline">
                    + Criar seu primeiro orçamento
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    const recent = state.projects.slice(0, 5);
    recentContainer.innerHTML = `
        <table class="w-full text-left text-xs">
            <thead>
                <tr class="border-b border-slate-800 text-slate-400">
                    <th class="py-2.5 px-3">Projeto</th>
                    <th class="py-2.5 px-3">Cliente</th>
                    <th class="py-2.5 px-3">Placas</th>
                    <th class="py-2.5 px-3">Tempo Est.</th>
                    <th class="py-2.5 px-3">Valor Final</th>
                    <th class="py-2.5 px-3">Status</th>
                    <th class="py-2.5 px-3 text-right">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60">
                ${recent.map(p => `
                    <tr class="hover:bg-slate-800/40 transition-colors">
                        <td class="py-3 px-3 font-semibold text-white">${p.name}</td>
                        <td class="py-3 px-3 text-slate-300">${p.client_name || '—'}</td>
                        <td class="py-3 px-3 text-slate-300">${p.plates_count}</td>
                        <td class="py-3 px-3 text-slate-300">${p.total_time_hours.toFixed(1)} h</td>
                        <td class="py-3 px-3 font-semibold text-blue-400">${formatCurrency(p.final_price_to_client)}</td>
                        <td class="py-3 px-3">
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold badge-${p.status}">
                                ${formatStatus(p.status)}
                            </span>
                        </td>
                        <td class="py-3 px-3 text-right">
                            <button onclick="editProject(${p.id})" class="p-1 hover:text-blue-400 transition-colors" title="Editar">
                                <i data-lucide="edit-3" class="w-4 h-4"></i>
                            </button>
                            <button onclick="API.pdf.download(${p.id}, 'client')" class="p-1 hover:text-emerald-400 transition-colors ml-1" title="PDF Cliente">
                                <i data-lucide="file-down" class="w-4 h-4"></i>
                            </button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    refreshIcons();
}

function formatStatus(status) {
    const map = {
        'draft': 'Rascunho',
        'quoted': 'Orçado',
        'approved': 'Aprovado',
        'in_production': 'Em Produção',
        'completed': 'Concluído',
        'cancelled': 'Cancelado',
    };
    return map[status] || status;
}

// ================= PROJECTS VIEW =================

function renderProjectsTable(filterText = '') {
    const container = document.getElementById('projects-table-container');
    if (!container) return;

    let items = state.projects;
    if (filterText) {
        const query = filterText.toLowerCase();
        items = items.filter(p => 
            p.name.toLowerCase().includes(query) || 
            (p.client_name && p.client_name.toLowerCase().includes(query))
        );
    }

    if (items.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-slate-400">
                <i data-lucide="folder-search" class="w-12 h-12 mx-auto mb-3 text-slate-600"></i>
                <p class="text-sm font-medium">Nenhum projeto encontrado.</p>
                <button onclick="openNewProject()" class="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold">
                    + Criar Novo Orçamento
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    container.innerHTML = `
        <table class="w-full text-left text-xs">
            <thead>
                <tr class="border-b border-slate-800 bg-slate-900/60 text-slate-400 uppercase tracking-wider">
                    <th class="py-3 px-4">Projeto</th>
                    <th class="py-3 px-4">Cliente</th>
                    <th class="py-3 px-4">Placas</th>
                    <th class="py-3 px-4">Tempo Total</th>
                    <th class="py-3 px-4">Custo Base</th>
                    <th class="py-3 px-4">Preço de Venda</th>
                    <th class="py-3 px-4">Status</th>
                    <th class="py-3 px-4 text-right">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
                ${items.map(p => `
                    <tr class="hover:bg-slate-800/40 transition-colors">
                        <td class="py-3.5 px-4 font-semibold text-white">${p.name}</td>
                        <td class="py-3.5 px-4 text-slate-300">${p.client_name || '—'}</td>
                        <td class="py-3.5 px-4 text-slate-300">${p.plates_count} un</td>
                        <td class="py-3.5 px-4 text-slate-300">${p.total_time_hours.toFixed(1)} h</td>
                        <td class="py-3.5 px-4 text-slate-400">${formatCurrency(p.base_cost)}</td>
                        <td class="py-3.5 px-4 font-bold text-blue-400 text-sm">${formatCurrency(p.final_price_to_client)}</td>
                        <td class="py-3.5 px-4">
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-semibold badge-${p.status}">
                                ${formatStatus(p.status)}
                            </span>
                        </td>
                        <td class="py-3.5 px-4 text-right">
                            <div class="flex items-center justify-end gap-1.5">
                                <button onclick="editProject(${p.id})" class="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors" title="Editar">
                                    <i data-lucide="edit" class="w-4 h-4"></i>
                                </button>
                                <button onclick="duplicateProject(${p.id})" class="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-slate-800 rounded transition-colors" title="Duplicar">
                                    <i data-lucide="copy" class="w-4 h-4"></i>
                                </button>
                                <button onclick="API.pdf.download(${p.id}, 'client')" class="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded transition-colors" title="PDF Orçamento">
                                    <i data-lucide="file-text" class="w-4 h-4"></i>
                                </button>
                                <button onclick="API.pdf.download(${p.id}, 'technical')" class="p-1.5 text-slate-400 hover:text-purple-400 hover:bg-slate-800 rounded transition-colors" title="Ficha Técnica">
                                    <i data-lucide="clipboard-list" class="w-4 h-4"></i>
                                </button>
                                <button onclick="deleteProject(${p.id})" class="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded transition-colors" title="Excluir">
                                    <i data-lucide="trash-2" class="w-4 h-4"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    refreshIcons();
}

function filterProjects() {
    const input = document.getElementById('project-search-input');
    renderProjectsTable(input ? input.value : '');
}

// ================= PROJECT CALCULATOR & EDITOR =================

function openNewProject() {
    state.currentProject = null;
    state.currentPlates = [createDefaultPlate(1)];
    state.currentBOM = [];

    // Prepopulate user defaults
    const u = state.user || {};
    document.getElementById('editor-project-title').textContent = 'Novo Orçamento';
    document.getElementById('editor-project-subtitle').textContent = 'Defina placas, arquivos 3MF/G-code e parâmetros comerciais';
    document.getElementById('proj-name').value = '';
    document.getElementById('proj-client-name').value = '';
    document.getElementById('proj-client-email').value = '';
    document.getElementById('proj-client-phone').value = '';
    document.getElementById('proj-status').value = 'draft';
    document.getElementById('proj-cad-hours').value = '0';
    document.getElementById('proj-cad-rate').value = u.default_cad_rate || '50';
    document.getElementById('proj-post-hours').value = '0';
    document.getElementById('proj-post-rate').value = u.default_post_rate || '30';
    document.getElementById('proj-overhead').value = '0';
    document.getElementById('proj-margin').value = u.default_profit_margin || '30';
    document.getElementById('proj-tax').value = u.default_tax_rate || '6';
    document.getElementById('proj-discount').value = '0';
    document.getElementById('proj-shipping').value = '0';
    document.getElementById('proj-notes').value = '';

    renderPlates();
    renderBOM();
    recalcLiveSummary();
    navigateTo('project-editor');
}

async function editProject(id) {
    try {
        const proj = await API.projects.get(id);
        state.currentProject = proj;
        state.currentPlates = (proj.plates && proj.plates.length > 0) ? proj.plates : [createDefaultPlate(1)];
        state.currentBOM = proj.bom_items || [];

        document.getElementById('editor-project-title').textContent = `Editar: ${proj.name}`;
        document.getElementById('editor-project-subtitle').textContent = `Orçamento #${proj.id.toString().padStart(4, '0')} • Cliente: ${proj.client_name || 'Não informado'}`;
        document.getElementById('proj-name').value = proj.name;
        document.getElementById('proj-client-name').value = proj.client_name || '';
        document.getElementById('proj-client-email').value = proj.client_email || '';
        document.getElementById('proj-client-phone').value = proj.client_phone || '';
        document.getElementById('proj-status').value = proj.status || 'draft';
        document.getElementById('proj-cad-hours').value = proj.cad_hours || 0;
        document.getElementById('proj-cad-rate').value = proj.cad_hourly_rate || 50;
        document.getElementById('proj-post-hours').value = proj.post_process_hours || 0;
        document.getElementById('proj-post-rate').value = proj.post_process_hourly_rate || 30;
        document.getElementById('proj-overhead').value = proj.overhead_cost || 0;
        document.getElementById('proj-margin').value = proj.profit_margin_percent || 30;
        document.getElementById('proj-tax').value = proj.tax_rate_percent || 6;
        document.getElementById('proj-discount').value = proj.discount_percent || 0;
        document.getElementById('proj-shipping').value = proj.shipping_cost || 0;
        document.getElementById('proj-notes').value = proj.notes || '';

        renderPlates();
        renderBOM();
        recalcLiveSummary();
        navigateTo('project-editor');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function createDefaultPlate(idx = 1) {
    const defaultPrinter = state.printers[0];
    const defaultFilament = state.filaments[0];

    return {
        name: `Placa ${idx}`,
        printer_id: defaultPrinter ? defaultPrinter.id : null,
        filament_id: defaultFilament ? defaultFilament.id : null,
        custom_printer_hourly_rate: defaultPrinter ? null : 2.50,
        custom_filament_cost_per_g: defaultFilament ? null : 0.10,
        print_time_hours: 0,
        part_weight_g: 0,
        purge_weight_g: 0,
        failure_margin_percent: (state.user && state.user.default_failure_rate) || 10,
        quantity: 1,
        notes: '',
    };
}

function addNewPlateRow() {
    const idx = state.currentPlates.length + 1;
    state.currentPlates.push(createDefaultPlate(idx));
    renderPlates();
    recalcLiveSummary();
}

function removePlateRow(index) {
    if (state.currentPlates.length <= 1) {
        showToast('O projeto precisa ter pelo menos uma placa.', 'info');
        return;
    }
    state.currentPlates.splice(index, 1);
    renderPlates();
    recalcLiveSummary();
}

function renderPlates() {
    const container = document.getElementById('plates-container');
    if (!container) return;

    container.innerHTML = state.currentPlates.map((plate, idx) => `
        <div class="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 relative group">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 font-bold text-xs flex items-center justify-center border border-blue-500/30">
                        ${idx + 1}
                    </span>
                    <input type="text" value="${plate.name}" oninput="state.currentPlates[${idx}].name = this.value" class="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs font-semibold text-white focus:outline-none focus:border-blue-500 w-44" placeholder="Nome da Placa">
                </div>

                <div class="flex items-center gap-2">
                    <label class="cursor-pointer px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] font-medium border border-slate-700 flex items-center gap-1 transition-colors" title="Carregar 3MF ou Gcode especificamente nesta placa">
                        <i data-lucide="upload" class="w-3 h-3 text-blue-400"></i> Importar 3MF/Gcode
                        <input type="file" accept=".3mf,.gcode" class="hidden" onchange="handleSinglePlateFile(event, ${idx})">
                    </label>
                    <button type="button" onclick="removePlateRow(${idx})" class="p-1 text-slate-400 hover:text-red-400 transition-colors" title="Remover Placa">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- Hardware & Filament selector -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                    <label class="block text-[11px] font-medium text-slate-400 mb-1">Impressora</label>
                    <select onchange="updatePlatePrinter(${idx}, this.value)" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-white focus:outline-none focus:border-blue-500">
                        <option value="">Personalizada (Definir R$/h manual)</option>
                        ${state.printers.map(p => `
                            <option value="${p.id}" ${plate.printer_id === p.id ? 'selected' : ''}>
                                ${p.name} (R$ ${p.machine_hourly_rate.toFixed(2)}/h)
                            </option>
                        `).join('')}
                    </select>
                </div>

                <div>
                    <label class="block text-[11px] font-medium text-slate-400 mb-1">Filamento</label>
                    <select onchange="updatePlateFilament(${idx}, this.value)" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-white focus:outline-none focus:border-blue-500">
                        <option value="">Personalizado (Definir R$/g manual)</option>
                        ${state.filaments.map(f => `
                            <option value="${f.id}" ${plate.filament_id === f.id ? 'selected' : ''}>
                                ${f.name} [${f.material}] (R$ ${f.cost_per_gram.toFixed(3)}/g)
                            </option>
                        `).join('')}
                    </select>
                </div>
            </div>

            <!-- Quantitative Inputs -->
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2 border-t border-slate-800/80">
                <div>
                    <label class="block text-[10px] font-medium text-slate-400 mb-0.5">Tempo (Horas)</label>
                    <input type="number" step="0.1" min="0" value="${plate.print_time_hours}" oninput="state.currentPlates[${idx}].print_time_hours = parseFloat(this.value)||0; recalcLiveSummary();" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-white">
                </div>
                <div>
                    <label class="block text-[10px] font-medium text-slate-400 mb-0.5">Peso Peça (g)</label>
                    <input type="number" step="1" min="0" value="${plate.part_weight_g}" oninput="state.currentPlates[${idx}].part_weight_g = parseFloat(this.value)||0; recalcLiveSummary();" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-white">
                </div>
                <div>
                    <label class="block text-[10px] font-medium text-slate-400 mb-0.5">Purga (g)</label>
                    <input type="number" step="1" min="0" value="${plate.purge_weight_g}" oninput="state.currentPlates[${idx}].purge_weight_g = parseFloat(this.value)||0; recalcLiveSummary();" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-white">
                </div>
                <div>
                    <label class="block text-[10px] font-medium text-slate-400 mb-0.5">Falha (%)</label>
                    <input type="number" step="1" min="0" value="${plate.failure_margin_percent}" oninput="state.currentPlates[${idx}].failure_margin_percent = parseFloat(this.value)||0; recalcLiveSummary();" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-white">
                </div>
                <div>
                    <label class="block text-[10px] font-medium text-slate-400 mb-0.5">Qtd Cópias</label>
                    <input type="number" step="1" min="1" value="${plate.quantity}" oninput="state.currentPlates[${idx}].quantity = parseInt(this.value,10)||1; recalcLiveSummary();" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-white font-bold">
                </div>
            </div>

            <!-- Single Plate Subtotal Pill -->
            <div class="flex items-center justify-between pt-1 text-[11px] text-slate-400">
                <span id="plate-summary-text-${idx}">Calculando custo da placa...</span>
                <span class="font-bold text-white" id="plate-cost-${idx}">R$ 0,00</span>
            </div>
        </div>
    `).join('');

    refreshIcons();
}

function updatePlatePrinter(idx, val) {
    state.currentPlates[idx].printer_id = val ? parseInt(val, 10) : null;
    recalcLiveSummary();
}

function updatePlateFilament(idx, val) {
    state.currentPlates[idx].filament_id = val ? parseInt(val, 10) : null;
    recalcLiveSummary();
}

// ================= BOM ITEMS (HARDWARE, SCREWS, ETC) =================

function createDefaultBOM() {
    return {
        name: 'Parafuso M3x12 Inox',
        category: 'Fixadores',
        quantity: 4,
        unit_cost: 0.50,
        notes: '',
    };
}

function addNewBomRow() {
    state.currentBOM.push(createDefaultBOM());
    renderBOM();
    recalcLiveSummary();
}

function removeBomRow(index) {
    state.currentBOM.splice(index, 1);
    renderBOM();
    recalcLiveSummary();
}

function renderBOM() {
    const container = document.getElementById('bom-container');
    if (!container) return;

    if (state.currentBOM.length === 0) {
        container.innerHTML = `
            <div class="p-4 rounded-lg bg-slate-900/40 border border-slate-800/80 text-center text-xs text-slate-400">
                Nenhum componente adicional (parafusos, insertos, eletrônica) adicionado ao projeto.
            </div>
        `;
        return;
    }

    container.innerHTML = state.currentBOM.map((item, idx) => `
        <div class="flex flex-wrap items-center gap-3 p-3 bg-slate-900/80 border border-slate-800 rounded-lg text-xs">
            <div class="flex-1 min-w-[140px]">
                <input type="text" value="${item.name}" oninput="state.currentBOM[${idx}].name = this.value" placeholder="Item (ex: Parafuso M3)" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-white">
            </div>
            <div class="w-28">
                <select onchange="state.currentBOM[${idx}].category = this.value" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-white">
                    <option value="Fixadores" ${item.category === 'Fixadores' ? 'selected' : ''}>Fixadores</option>
                    <option value="Insertos" ${item.category === 'Insertos' ? 'selected' : ''}>Insertos</option>
                    <option value="Eletrônica" ${item.category === 'Eletrônica' ? 'selected' : ''}>Eletrônica</option>
                    <option value="Embalagem" ${item.category === 'Embalagem' ? 'selected' : ''}>Embalagem</option>
                    <option value="Outros" ${item.category === 'Outros' ? 'selected' : ''}>Outros</option>
                </select>
            </div>
            <div class="w-16">
                <input type="number" min="1" step="1" value="${item.quantity}" oninput="state.currentBOM[${idx}].quantity = parseInt(this.value,10)||1; recalcLiveSummary();" placeholder="Qtd" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-white text-center font-bold">
            </div>
            <div class="w-24">
                <input type="number" min="0" step="0.05" value="${item.unit_cost}" oninput="state.currentBOM[${idx}].unit_cost = parseFloat(this.value)||0; recalcLiveSummary();" placeholder="R$ Unit" class="w-full px-2 py-1 bg-slate-800 border border-slate-700 rounded text-white">
            </div>
            <div class="w-24 text-right font-bold text-white" id="bom-subtotal-${idx}">
                ${formatCurrency((item.quantity || 1) * (item.unit_cost || 0))}
            </div>
            <button type="button" onclick="removeBomRow(${idx})" class="p-1 text-slate-400 hover:text-red-400 transition-colors">
                <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
        </div>
    `).join('');

    refreshIcons();
}

// ================= REAL-TIME CLIENT-SIDE FINANCIAL CALCULATION =================

function recalcLiveSummary() {
    const printersMap = {};
    state.printers.forEach(p => { printersMap[p.id] = p; });

    const filamentsMap = {};
    state.filaments.forEach(f => { filamentsMap[f.id] = f; });

    let totalPlatesCost = 0;
    let totalMaterialCost = 0;
    let totalMachineCost = 0;
    let totalTimeHours = 0;
    let totalWeightGrams = 0;

    // 1. Plates math
    state.currentPlates.forEach((plate, idx) => {
        const printer = plate.printer_id ? printersMap[plate.printer_id] : null;
        const filament = plate.filament_id ? filamentsMap[plate.filament_id] : null;

        // Cost per gram
        let costPerGram = 0;
        if (filament && filament.spool_weight_g > 0) {
            costPerGram = filament.spool_price / filament.spool_weight_g;
        } else if (plate.custom_filament_cost_per_g) {
            costPerGram = plate.custom_filament_cost_per_g;
        } else {
            costPerGram = 0.09; // fallback standard PLA
        }

        // Machine rate
        let machineHourlyRate = 0;
        if (printer) {
            machineHourlyRate = printer.machine_hourly_rate || 2.0;
        } else if (plate.custom_printer_hourly_rate) {
            machineHourlyRate = plate.custom_printer_hourly_rate;
        } else {
            machineHourlyRate = 2.0; // fallback standard rate
        }

        const qty = plate.quantity || 1;
        const printTime = plate.print_time_hours || 0;
        const rawWeight = (plate.part_weight_g || 0) + (plate.purge_weight_g || 0);
        const failureFactor = 1.0 + ((plate.failure_margin_percent || 0) / 100);
        const effectiveWeight = rawWeight * failureFactor;

        const unitMaterialCost = effectiveWeight * costPerGram;
        const unitMachineCost = printTime * machineHourlyRate;
        const unitTotalCost = unitMaterialCost + unitMachineCost;

        const plateTotalCost = unitTotalCost * qty;
        totalPlatesCost += plateTotalCost;
        totalMaterialCost += unitMaterialCost * qty;
        totalMachineCost += unitMachineCost * qty;
        totalTimeHours += printTime * qty;
        totalWeightGrams += rawWeight * qty;

        // Update single plate cost pill
        const costEl = document.getElementById(`plate-cost-${idx}`);
        const sumTextEl = document.getElementById(`plate-summary-text-${idx}`);
        if (costEl) costEl.textContent = formatCurrency(plateTotalCost);
        if (sumTextEl) {
            sumTextEl.textContent = `${qty}x • ${(printTime * qty).toFixed(1)}h • ${(rawWeight * qty).toFixed(1)}g (Mat: ${formatCurrency(unitMaterialCost * qty)} + Máq: ${formatCurrency(unitMachineCost * qty)})`;
        }
    });

    // 2. BOM Items math
    let totalBOMCost = 0;
    state.currentBOM.forEach((item, idx) => {
        const qty = item.quantity || 1;
        const unit = item.unit_cost || 0;
        const subtotal = qty * unit;
        totalBOMCost += subtotal;
        const subEl = document.getElementById(`bom-subtotal-${idx}`);
        if (subEl) subEl.textContent = formatCurrency(subtotal);
    });

    // 3. Labor costs
    const cadHours = parseFloat(document.getElementById('proj-cad-hours')?.value || 0);
    const cadRate = parseFloat(document.getElementById('proj-cad-rate')?.value || 50);
    const cadCost = cadHours * cadRate;

    const postHours = parseFloat(document.getElementById('proj-post-hours')?.value || 0);
    const postRate = parseFloat(document.getElementById('proj-post-rate')?.value || 30);
    const postCost = postHours * postRate;

    const totalLaborCost = cadCost + postCost;

    // 4. Overhead & Base Cost
    const overheadCost = parseFloat(document.getElementById('proj-overhead')?.value || 0);
    const baseCost = totalPlatesCost + totalBOMCost + totalLaborCost + overheadCost;

    // 5. Pricing, Margins, Taxes
    const marginPercent = parseFloat(document.getElementById('proj-margin')?.value || 30);
    const taxPercent = Math.min(99, parseFloat(document.getElementById('proj-tax')?.value || 6));
    const discountPercent = Math.min(100, parseFloat(document.getElementById('proj-discount')?.value || 0));
    const shippingCost = parseFloat(document.getElementById('proj-shipping')?.value || 0);

    const taxDivisor = Math.max(0.01, 1.0 - (taxPercent / 100.0));
    const suggestedPrice = baseCost > 0 ? ((baseCost * (1.0 + (marginPercent / 100.0))) / taxDivisor) : 0;

    const discountAmount = suggestedPrice * (discountPercent / 100.0);
    const subtotalAfterDiscount = suggestedPrice - discountAmount;
    const taxAmount = subtotalAfterDiscount * (taxPercent / 100.0);
    const netRevenue = subtotalAfterDiscount - taxAmount;
    const netProfit = netRevenue - baseCost;
    const effectiveMarginPercent = baseCost > 0 ? (netProfit / baseCost * 100.0) : 0;
    const finalPriceToClient = subtotalAfterDiscount + shippingCost;

    // Update Live Summary DOM
    setText('live-weight', `${totalWeightGrams.toFixed(1)} g`);
    setText('live-time', `${totalTimeHours.toFixed(1)} h`);
    setText('live-material-cost', formatCurrency(totalMaterialCost));
    setText('live-machine-cost', formatCurrency(totalMachineCost));
    setText('live-bom-cost', formatCurrency(totalBOMCost));
    setText('live-labor-cost', formatCurrency(totalLaborCost));
    setText('live-overhead-cost', formatCurrency(overheadCost));
    setText('live-base-cost', formatCurrency(baseCost));
    setText('live-suggested-price', formatCurrency(suggestedPrice));
    setText('live-discount-amount', `- ${formatCurrency(discountAmount)}`);
    setText('live-shipping-amount', `+ ${formatCurrency(shippingCost)}`);
    setText('live-tax-amount', formatCurrency(taxAmount));
    setText('live-final-price', formatCurrency(finalPriceToClient));
    setText('live-net-profit', `${formatCurrency(netProfit)} (${effectiveMarginPercent.toFixed(1)}%)`);
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

// ================= SAVING & EXPORTING =================

async function saveCurrentProject() {
    const name = document.getElementById('proj-name').value.trim();
    if (!name) {
        showToast('Por favor, informe o título do projeto.', 'error');
        document.getElementById('proj-name').focus();
        return;
    }

    const payload = {
        name,
        client_name: document.getElementById('proj-client-name').value.trim(),
        client_email: document.getElementById('proj-client-email').value.trim(),
        client_phone: document.getElementById('proj-client-phone').value.trim(),
        status: document.getElementById('proj-status').value,
        cad_hours: parseFloat(document.getElementById('proj-cad-hours').value) || 0,
        cad_hourly_rate: parseFloat(document.getElementById('proj-cad-rate').value) || 0,
        post_process_hours: parseFloat(document.getElementById('proj-post-hours').value) || 0,
        post_process_hourly_rate: parseFloat(document.getElementById('proj-post-rate').value) || 0,
        overhead_cost: parseFloat(document.getElementById('proj-overhead').value) || 0,
        profit_margin_percent: parseFloat(document.getElementById('proj-margin').value) || 0,
        tax_rate_percent: parseFloat(document.getElementById('proj-tax').value) || 0,
        discount_percent: parseFloat(document.getElementById('proj-discount').value) || 0,
        shipping_cost: parseFloat(document.getElementById('proj-shipping').value) || 0,
        notes: document.getElementById('proj-notes').value.trim(),
        plates: state.currentPlates.map(p => ({
            name: p.name,
            printer_id: p.printer_id,
            filament_id: p.filament_id,
            custom_printer_hourly_rate: p.custom_printer_hourly_rate,
            custom_filament_cost_per_g: p.custom_filament_cost_per_g,
            print_time_hours: p.print_time_hours,
            part_weight_g: p.part_weight_g,
            purge_weight_g: p.purge_weight_g,
            failure_margin_percent: p.failure_margin_percent,
            quantity: p.quantity,
            notes: p.notes,
        })),
        bom_items: state.currentBOM.map(b => ({
            name: b.name,
            category: b.category,
            quantity: b.quantity,
            unit_cost: b.unit_cost,
            notes: b.notes,
        })),
    };

    try {
        if (state.currentProject && state.currentProject.id) {
            // Update existing
            const updated = await API.projects.update(state.currentProject.id, payload);
            showToast('Projeto atualizado com sucesso!', 'success');
            state.currentProject = updated;
        } else {
            // Create new
            const created = await API.projects.create(payload);
            showToast('Projeto criado com sucesso!', 'success');
            state.currentProject = created;
        }

        await loadAllData();
        navigateTo('projects');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function exportCurrentPdf(type = 'client') {
    if (!state.currentProject || !state.currentProject.id) {
        showToast('Salve o projeto antes de exportar o PDF.', 'info');
        return;
    }
    try {
        showToast('Gerando documento PDF profissional...', 'info');
        await API.pdf.download(state.currentProject.id, type);
        showToast('Download do PDF concluído!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function duplicateProject(id) {
    try {
        await API.projects.duplicate(id);
        showToast('Projeto duplicado com sucesso!', 'success');
        await loadAllData();
        renderProjectsTable();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteProject(id) {
    if (!confirm('Deseja realmente excluir este orçamento?')) return;
    try {
        await API.projects.delete(id);
        showToast('Projeto excluído com sucesso.', 'success');
        await loadAllData();
        renderProjectsTable();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ================= FILE IMPORT HANDLERS (HYBRID 3MF / G-CODE) =================

function setupDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-slicer-input');

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleSlicerFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleSlicerFile(e.target.files[0]);
        }
    });
}

async function handleSlicerFile(file) {
    const name = file.name.toLowerCase();
    showToast(`Processando metadados de ${file.name}...`, 'info');

    try {
        if (name.endsWith('.3mf')) {
            const extractedPlates = await parse3mfMetadata(file);
            if (extractedPlates && extractedPlates.length > 0) {
                // If only 1 empty plate exists, replace it, else append
                if (state.currentPlates.length === 1 && state.currentPlates[0].print_time_hours === 0 && state.currentPlates[0].part_weight_g === 0) {
                    state.currentPlates = extractedPlates;
                } else {
                    state.currentPlates = [...state.currentPlates, ...extractedPlates];
                }
                showToast(`Arquivo 3MF lido! ${extractedPlates.length} placa(s) adicionada(s).`, 'success');
            }
        } else if (name.endsWith('.gcode')) {
            const text = await file.text();
            const meta = parseGcodeMetadata(text);
            const newPlate = createDefaultPlate(state.currentPlates.length + 1);
            newPlate.name = file.name.replace(/\.gcode$/i, '');
            newPlate.print_time_hours = meta.print_time_hours;
            newPlate.part_weight_g = meta.part_weight_g;

            if (state.currentPlates.length === 1 && state.currentPlates[0].print_time_hours === 0 && state.currentPlates[0].part_weight_g === 0) {
                state.currentPlates = [newPlate];
            } else {
                state.currentPlates.push(newPlate);
            }
            showToast(`G-Code lido com sucesso (${meta.print_time_hours}h, ${meta.part_weight_g}g)!`, 'success');
        } else {
            showToast('Formato não suportado. Utilize arquivos .3mf ou .gcode.', 'error');
            return;
        }

        renderPlates();
        recalcLiveSummary();
    } catch (err) {
        showToast(`Erro ao ler arquivo: ${err.message}`, 'error');
    }
}

async function handleSinglePlateFile(e, plateIdx) {
    const file = e.target.files[0];
    if (!file) return;

    try {
        const name = file.name.toLowerCase();
        if (name.endsWith('.3mf')) {
            const plates = await parse3mfMetadata(file);
            if (plates.length > 0) {
                state.currentPlates[plateIdx].print_time_hours = plates[0].print_time_hours;
                state.currentPlates[plateIdx].part_weight_g = plates[0].part_weight_g;
                state.currentPlates[plateIdx].purge_weight_g = plates[0].purge_weight_g;
                showToast(`Placa atualizada com dados do 3MF!`, 'success');
            }
        } else if (name.endsWith('.gcode')) {
            const text = await file.text();
            const meta = parseGcodeMetadata(text);
            state.currentPlates[plateIdx].print_time_hours = meta.print_time_hours;
            state.currentPlates[plateIdx].part_weight_g = meta.part_weight_g;
            showToast(`Placa atualizada com dados do G-Code!`, 'success');
        }
        renderPlates();
        recalcLiveSummary();
    } catch (err) {
        showToast(`Erro ao carregar arquivo: ${err.message}`, 'error');
    }
}

// ================= PRINTERS CRUD =================

function openPrinterModal(printer = null) {
    const modal = document.getElementById('modal-printer');
    const title = document.getElementById('modal-printer-title');
    modal.classList.remove('hidden');

    if (printer) {
        title.innerHTML = `<i data-lucide="printer" class="w-5 h-5 text-blue-400"></i> Editar Impressora`;
        document.getElementById('printer-id').value = printer.id;
        document.getElementById('printer-name').value = printer.name;
        document.getElementById('printer-model').value = printer.model || '';
        document.getElementById('printer-cost').value = printer.acquisition_cost;
        document.getElementById('printer-lifespan').value = printer.lifespan_hours;
        document.getElementById('printer-power').value = printer.avg_power_watts;
        document.getElementById('printer-maintenance').value = printer.maintenance_cost_per_hour;
        document.getElementById('printer-energy').value = printer.energy_rate_kwh;
    } else {
        title.innerHTML = `<i data-lucide="printer" class="w-5 h-5 text-blue-400"></i> Cadastrar Impressora`;
        document.getElementById('printer-id').value = '';
        document.getElementById('printer-name').value = '';
        document.getElementById('printer-model').value = '';
        document.getElementById('printer-cost').value = '3500';
        document.getElementById('printer-lifespan').value = '5000';
        document.getElementById('printer-power').value = '150';
        document.getElementById('printer-maintenance').value = '1.0';
        document.getElementById('printer-energy').value = (state.user && state.user.default_energy_rate) || '0.85';
    }
    refreshIcons();
}

function closePrinterModal() {
    document.getElementById('modal-printer').classList.add('hidden');
}

async function handleSavePrinter(e) {
    e.preventDefault();
    const id = document.getElementById('printer-id').value;
    const payload = {
        name: document.getElementById('printer-name').value.trim(),
        model: document.getElementById('printer-model').value.trim(),
        acquisition_cost: parseFloat(document.getElementById('printer-cost').value) || 0,
        lifespan_hours: parseFloat(document.getElementById('printer-lifespan').value) || 5000,
        avg_power_watts: parseFloat(document.getElementById('printer-power').value) || 150,
        maintenance_cost_per_hour: parseFloat(document.getElementById('printer-maintenance').value) || 1.0,
        energy_rate_kwh: parseFloat(document.getElementById('printer-energy').value) || 0.85,
    };

    try {
        if (id) {
            await API.printers.update(id, payload);
            showToast('Impressora atualizada com sucesso!', 'success');
        } else {
            await API.printers.create(payload);
            showToast('Impressora cadastrada com sucesso!', 'success');
        }
        closePrinterModal();
        await loadAllData();
        renderPrintersGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deletePrinter(id) {
    if (!confirm('Deseja realmente remover esta impressora?')) return;
    try {
        await API.printers.delete(id);
        showToast('Impressora removida.', 'success');
        await loadAllData();
        renderPrintersGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function renderPrintersGrid() {
    const grid = document.getElementById('printers-grid');
    if (!grid) return;

    if (state.printers.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full card-dark p-12 text-center text-slate-400">
                <i data-lucide="printer" class="w-12 h-12 mx-auto mb-3 text-slate-600"></i>
                <h4 class="text-base font-bold text-white">Nenhuma impressora cadastrada</h4>
                <p class="text-xs text-slate-400 mt-1 max-w-md mx-auto">Cadastre suas impressoras reais para calcular depreciação por hora de uso, custo em kWh de energia elétrica e manutenção preventiva.</p>
                <button onclick="openPrinterModal()" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold">
                    + Cadastrar Impressora
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    grid.innerHTML = state.printers.map(p => {
        const rates = p.rates_breakdown || {};
        return `
            <div class="card-dark p-6 space-y-4 hover:border-slate-600 transition-all flex flex-col justify-between">
                <div>
                    <div class="flex items-start justify-between">
                        <div>
                            <h4 class="font-bold text-white text-base">${p.name}</h4>
                            <p class="text-xs text-slate-400">${p.model || 'FDM'}</p>
                        </div>
                        <div class="flex items-center gap-1">
                            <button onclick='openPrinterModal(${JSON.stringify(p)})' class="p-1 text-slate-400 hover:text-white transition-colors" title="Editar">
                                <i data-lucide="edit-2" class="w-4 h-4"></i>
                            </button>
                            <button onclick="deletePrinter(${p.id})" class="p-1 text-slate-400 hover:text-red-400 transition-colors" title="Excluir">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Highlighted Machine Rate -->
                    <div class="mt-4 p-3 rounded-lg bg-blue-950/30 border border-blue-800/40 text-center">
                        <span class="text-[10px] uppercase font-semibold text-blue-300 tracking-wider">Tarifa Horária Total</span>
                        <div class="text-2xl font-black text-blue-400 mt-0.5">
                            ${formatCurrency(p.machine_hourly_rate)}<span class="text-xs font-normal text-slate-400">/h</span>
                        </div>
                    </div>

                    <!-- Breakdown Table -->
                    <div class="mt-4 space-y-2 text-xs text-slate-300">
                        <div class="flex justify-between">
                            <span class="text-slate-400">Depreciação:</span>
                            <span>${formatCurrency(rates.depreciation_per_hour || 0)}/h</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-slate-400">Energia (${p.avg_power_watts}W):</span>
                            <span>${formatCurrency(rates.energy_cost_per_hour || 0)}/h</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-slate-400">Reserva Manutenção:</span>
                            <span>${formatCurrency(rates.maintenance_cost_per_hour || 0)}/h</span>
                        </div>
                    </div>
                </div>

                <div class="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
                    <span>Vida útil: ${p.lifespan_hours} h</span>
                    <span>Aquisição: ${formatCurrency(p.acquisition_cost)}</span>
                </div>
            </div>
        `;
    }).join('');
    refreshIcons();
}

// ================= FILAMENTS CRUD =================

function openFilamentModal(filament = null) {
    const modal = document.getElementById('modal-filament');
    const title = document.getElementById('modal-filament-title');
    modal.classList.remove('hidden');

    if (filament) {
        title.innerHTML = `<i data-lucide="cylinder" class="w-5 h-5 text-blue-400"></i> Editar Filamento`;
        document.getElementById('filament-id').value = filament.id;
        document.getElementById('filament-name').value = filament.name;
        document.getElementById('filament-brand').value = filament.brand || '';
        document.getElementById('filament-material').value = filament.material || 'PLA';
        document.getElementById('filament-color').value = filament.color || '';
        document.getElementById('filament-weight').value = filament.spool_weight_g;
        document.getElementById('filament-price').value = filament.spool_price;
    } else {
        title.innerHTML = `<i data-lucide="cylinder" class="w-5 h-5 text-blue-400"></i> Cadastrar Filamento`;
        document.getElementById('filament-id').value = '';
        document.getElementById('filament-name').value = '';
        document.getElementById('filament-brand').value = '';
        document.getElementById('filament-material').value = 'PLA';
        document.getElementById('filament-color').value = '';
        document.getElementById('filament-weight').value = '1000';
        document.getElementById('filament-price').value = '90';
    }
    refreshIcons();
}

function closeFilamentModal() {
    document.getElementById('modal-filament').classList.add('hidden');
}

async function handleSaveFilament(e) {
    e.preventDefault();
    const id = document.getElementById('filament-id').value;
    const payload = {
        name: document.getElementById('filament-name').value.trim(),
        brand: document.getElementById('filament-brand').value.trim(),
        material: document.getElementById('filament-material').value,
        color: document.getElementById('filament-color').value.trim(),
        spool_weight_g: parseFloat(document.getElementById('filament-weight').value) || 1000,
        spool_price: parseFloat(document.getElementById('filament-price').value) || 90,
    };

    try {
        if (id) {
            await API.filaments.update(id, payload);
            showToast('Filamento atualizado com sucesso!', 'success');
        } else {
            await API.filaments.create(payload);
            showToast('Filamento cadastrado com sucesso!', 'success');
        }
        closeFilamentModal();
        await loadAllData();
        renderFilamentsGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteFilament(id) {
    if (!confirm('Deseja realmente remover este filamento?')) return;
    try {
        await API.filaments.delete(id);
        showToast('Filamento removido.', 'success');
        await loadAllData();
        renderFilamentsGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function renderFilamentsGrid() {
    const grid = document.getElementById('filaments-grid');
    if (!grid) return;

    if (state.filaments.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full card-dark p-12 text-center text-slate-400">
                <i data-lucide="cylinder" class="w-12 h-12 mx-auto mb-3 text-slate-600"></i>
                <h4 class="text-base font-bold text-white">Nenhum filamento cadastrado</h4>
                <p class="text-xs text-slate-400 mt-1 max-w-md mx-auto">Cadastre suas marcas e carretéis reais para apurar o custo exato em gramas de cada projeto impresso.</p>
                <button onclick="openFilamentModal()" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold">
                    + Cadastrar Filamento
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    grid.innerHTML = state.filaments.map(f => {
        const matLower = (f.material || 'other').toLowerCase();
        return `
            <div class="card-dark p-6 space-y-4 hover:border-slate-600 transition-all flex flex-col justify-between">
                <div>
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider badge-mat-${matLower}">
                                    ${f.material}
                                </span>
                                <h4 class="font-bold text-white text-sm">${f.name}</h4>
                            </div>
                            <p class="text-xs text-slate-400 mt-1">${f.brand || 'Genérico'} • ${f.color || 'Cor padrão'}</p>
                        </div>
                        <div class="flex items-center gap-1">
                            <button onclick='openFilamentModal(${JSON.stringify(f)})' class="p-1 text-slate-400 hover:text-white transition-colors" title="Editar">
                                <i data-lucide="edit-2" class="w-4 h-4"></i>
                            </button>
                            <button onclick="deleteFilament(${f.id})" class="p-1 text-slate-400 hover:text-red-400 transition-colors" title="Excluir">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Highlighted Gram Cost -->
                    <div class="mt-4 p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-center">
                        <span class="text-[10px] uppercase font-semibold text-emerald-300 tracking-wider">Custo por Grama</span>
                        <div class="text-2xl font-black text-emerald-400 mt-0.5">
                            R$ ${f.cost_per_gram.toFixed(4)}<span class="text-xs font-normal text-slate-400">/g</span>
                        </div>
                    </div>
                </div>

                <div class="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
                    <span>Carretel: ${f.spool_weight_g} g</span>
                    <span>Preço: ${formatCurrency(f.spool_price)}</span>
                </div>
            </div>
        `;
    }).join('');
    refreshIcons();
}

// ================= SETTINGS & PREFERENCES =================

function populateSettingsForm() {
    const u = state.user;
    if (!u) return;

    document.getElementById('pref-company').value = u.company_name || '';
    document.getElementById('pref-fullname').value = u.full_name || '';
    document.getElementById('pref-phone').value = u.phone || '';
    document.getElementById('pref-pix').value = u.pix_key || '';
    document.getElementById('pref-energy').value = u.default_energy_rate || 0.85;
    document.getElementById('pref-margin').value = u.default_profit_margin || 30;
    document.getElementById('pref-tax').value = u.default_tax_rate || 6;
    document.getElementById('pref-failure').value = u.default_failure_rate || 10;
    document.getElementById('pref-cad-rate').value = u.default_cad_rate || 50;
    document.getElementById('pref-post-rate').value = u.default_post_rate || 30;
}

async function handleSavePreferences(e) {
    e.preventDefault();
    const payload = {
        company_name: document.getElementById('pref-company').value.trim(),
        full_name: document.getElementById('pref-fullname').value.trim(),
        phone: document.getElementById('pref-phone').value.trim(),
        pix_key: document.getElementById('pref-pix').value.trim(),
        default_energy_rate: parseFloat(document.getElementById('pref-energy').value) || 0.85,
        default_profit_margin: parseFloat(document.getElementById('pref-margin').value) || 30,
        default_tax_rate: parseFloat(document.getElementById('pref-tax').value) || 6,
        default_failure_rate: parseFloat(document.getElementById('pref-failure').value) || 10,
        default_cad_rate: parseFloat(document.getElementById('pref-cad-rate').value) || 50,
        default_post_rate: parseFloat(document.getElementById('pref-post-rate').value) || 30,
    };

    try {
        const updated = await API.auth.updatePreferences(payload);
        state.user = updated;
        updateUserUI();
        showToast('Preferências salvas com sucesso!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ================= INITIALIZATION =================

window.addEventListener('DOMContentLoaded', async () => {
    refreshIcons();
    setupDropzone();

    window.addEventListener('auth:unauthorized', () => {
        document.getElementById('auth-modal').classList.remove('hidden');
    });

    window.addEventListener('auth:logout', () => {
        state.user = null;
        document.getElementById('auth-modal').classList.remove('hidden');
    });

    const token = API.getToken();
    if (token) {
        try {
            state.user = await API.auth.getMe();
            document.getElementById('auth-modal').classList.add('hidden');
            updateUserUI();
            await loadAllData();
            navigateTo('dashboard');
        } catch (err) {
            API.auth.clearSession();
            document.getElementById('auth-modal').classList.remove('hidden');
        }
    } else {
        document.getElementById('auth-modal').classList.remove('hidden');
    }
});
