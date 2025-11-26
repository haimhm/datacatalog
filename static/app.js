let allProducts = [];
let filteredProducts = [];
let currentFilters = { categories: [], statuses: [], stages: [], regions: [], vendors: [] };
let currentView = 'list';
let currentUser = null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    await loadFilters();
    await loadProducts();
    setupEventListeners();
});

async function checkAuth() {
    const res = await fetch('/api/user');
    currentUser = await res.json();
    updateAuthUI();
}

function updateAuthUI() {
    const authSection = document.getElementById('authSection');
    if (currentUser.authenticated) {
        const roleClass = currentUser.role === 'admin' ? 'admin' : '';
        authSection.innerHTML = `
            <div class="user-info">
                <span>${currentUser.username}</span>
                <span class="role-badge ${roleClass}">${currentUser.role}</span>
            </div>
            <button id="logoutBtn" class="btn btn-secondary">Sign Out</button>
        `;
        document.getElementById('logoutBtn').addEventListener('click', logout);
    } else {
        authSection.innerHTML = `<button id="loginBtn" class="btn btn-primary">Sign In</button>`;
        document.getElementById('loginBtn').addEventListener('click', () => showModal('loginModal'));
    }
}

async function loadFilters() {
    const res = await fetch('/api/filters');
    const filters = await res.json();
    
    renderFilterList('categoryFilters', filters.categories, 'categories');
    renderFilterList('statusFilters', filters.statuses, 'statuses');
    renderFilterList('stageFilters', filters.stages, 'stages');
    renderFilterList('regionFilters', filters.regions, 'regions');
    renderFilterList('vendorFilters', filters.vendors, 'vendors');
}

function renderFilterList(containerId, items, filterKey) {
    const container = document.getElementById(containerId);
    container.innerHTML = items.map(item => `
        <label class="filter-item">
            <input type="checkbox" value="${item}" data-filter="${filterKey}">
            <span>${item}</span>
        </label>
    `).join('');
}

async function loadProducts() {
    const res = await fetch('/api/products');
    allProducts = await res.json();
    filteredProducts = [...allProducts];
    updateStats();
    renderProducts();
}

function updateStats() {
    document.getElementById('totalDatasets').textContent = allProducts.length;
    document.getElementById('totalVendors').textContent = new Set(allProducts.map(p => p.vendor).filter(Boolean)).size;
    document.getElementById('totalCategories').textContent = new Set(allProducts.map(p => p.datatype).filter(Boolean)).size;
}

function renderProducts() {
    const container = document.getElementById('productList');
    container.className = `product-list ${currentView === 'grid' ? 'grid' : ''}`;
    
    document.getElementById('resultsCount').textContent = `${filteredProducts.length} results`;
    
    container.innerHTML = filteredProducts.map(p => `
        <div class="product-card" data-id="${p.id}">
            <div class="product-title">${p.short_desc || p.data_ID}</div>
            <div class="product-vendor">by ${p.vendor || 'Unknown'}</div>
            <div class="product-meta">
                ${p.datatype ? `<span class="tag category">${p.datatype}</span>` : ''}
                ${p.region ? `<span class="tag region">${p.region}</span>` : ''}
                ${p.status ? `<span class="tag status">${p.status}</span>` : ''}
            </div>
            <div class="product-desc">${p.long_desc || ''}</div>
            <div class="product-footer">
                <span class="tag">${p.delivery_frequency || 'N/A'}</span>
                <span class="view-link">View Product →</span>
            </div>
        </div>
    `).join('');
}

function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    filteredProducts = allProducts.filter(p => {
        // Search filter
        const searchMatch = !searchTerm || 
            (p.short_desc && p.short_desc.toLowerCase().includes(searchTerm)) ||
            (p.long_desc && p.long_desc.toLowerCase().includes(searchTerm)) ||
            (p.vendor && p.vendor.toLowerCase().includes(searchTerm)) ||
            (p.data_ID && p.data_ID.toLowerCase().includes(searchTerm));
        
        // Category filter
        const categoryMatch = currentFilters.categories.length === 0 || 
            currentFilters.categories.includes(p.datatype);
        
        // Status filter
        const statusMatch = currentFilters.statuses.length === 0 || 
            currentFilters.statuses.includes(p.status);
        
        // Stage filter
        const stageMatch = currentFilters.stages.length === 0 || 
            currentFilters.stages.includes(p.stage);
        
        // Region filter
        const regionMatch = currentFilters.regions.length === 0 || 
            currentFilters.regions.includes(p.region);
        
        // Vendor filter
        const vendorMatch = currentFilters.vendors.length === 0 || 
            currentFilters.vendors.includes(p.vendor);
        
        return searchMatch && categoryMatch && statusMatch && stageMatch && regionMatch && vendorMatch;
    });
    
    renderProducts();
}

function setupEventListeners() {
    // Search
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    
    // Filter checkboxes
    document.getElementById('sidebar').addEventListener('change', (e) => {
        if (e.target.type === 'checkbox') {
            const filterKey = e.target.dataset.filter;
            const value = e.target.value;
            if (e.target.checked) {
                currentFilters[filterKey].push(value);
            } else {
                currentFilters[filterKey] = currentFilters[filterKey].filter(v => v !== value);
            }
            applyFilters();
        }
    });
    
    // Clear filters
    document.getElementById('clearFilters').addEventListener('click', () => {
        currentFilters = { categories: [], statuses: [], stages: [], regions: [], vendors: [] };
        document.querySelectorAll('#sidebar input[type="checkbox"]').forEach(cb => cb.checked = false);
        document.getElementById('searchInput').value = '';
        applyFilters();
    });
    
    // View toggle
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentView = btn.dataset.view;
            renderProducts();
        });
    });
    
    // Product click
    document.getElementById('productList').addEventListener('click', async (e) => {
        const card = e.target.closest('.product-card');
        if (card) {
            const id = card.dataset.id;
            await showProductDetail(id);
        }
    });
    
    // Login form
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await login();
    });
    
    // Modal close
    document.querySelectorAll('.close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.remove('active');
        });
    });
    
    // Close modal on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('active');
        });
    });
}

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    
    const data = await res.json();
    if (data.success) {
        hideModal('loginModal');
        await checkAuth();
        await loadProducts();
    } else {
        document.getElementById('loginError').textContent = data.error;
    }
}

async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    await checkAuth();
    await loadProducts();
}

async function showProductDetail(id) {
    const res = await fetch(`/api/products/${id}`);
    const product = await res.json();
    
    const sensitiveFields = ['user', 'contract_start', 'contract_end', 'term', 'annual_cost', 'price_cap', 'use_permissions', 'notes'];
    const isAdmin = currentUser && currentUser.role === 'admin';
    
    const detailContent = document.getElementById('detailContent');
    detailContent.innerHTML = `
        <div class="detail-header">
            <div class="detail-title">${product.short_desc || product.data_ID}</div>
            <div class="detail-vendor">by ${product.vendor || 'Unknown'}</div>
        </div>
        <div class="detail-body">
            <div class="detail-main">
                <h3>About this dataset</h3>
                <p class="detail-desc">${product.long_desc || 'No description available.'}</p>
            </div>
            <div class="detail-sidebar">
                <div class="detail-field">
                    <div class="detail-field-label">Category</div>
                    <div class="detail-field-value">${product.datatype || 'N/A'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Region</div>
                    <div class="detail-field-value">${product.region || 'N/A'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Status</div>
                    <div class="detail-field-value">${product.status || 'N/A'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Stage</div>
                    <div class="detail-field-value">${product.stage || 'N/A'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Delivery Frequency</div>
                    <div class="detail-field-value">${product.delivery_frequency || 'N/A'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-field-label">Delivery Method</div>
                    <div class="detail-field-value">${product.delivery_method || 'N/A'}</div>
                </div>
                ${isAdmin ? sensitiveFields.map(field => `
                    <div class="detail-field">
                        <div class="detail-field-label">${field.replace(/_/g, ' ')}<span class="sensitive-badge">Admin Only</span></div>
                        <div class="detail-field-value">${product[field] || 'N/A'}</div>
                    </div>
                `).join('') : ''}
            </div>
        </div>
    `;
    
    showModal('detailModal');
}

function showModal(id) {
    document.getElementById(id).classList.add('active');
}

function hideModal(id) {
    document.getElementById(id).classList.remove('active');
}

