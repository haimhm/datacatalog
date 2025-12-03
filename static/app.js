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
        const addBtn = currentUser.role === 'admin' ? `<button id="addProductBtn" class="btn btn-secondary">+ Add Dataset</button><button id="manageUsersBtn" class="btn btn-secondary">Users</button><button id="manageOptionsBtn" class="btn btn-secondary">Column Options</button>` : '';
        authSection.innerHTML = `
            ${addBtn}
            <div class="user-info">
                <span>${currentUser.username}</span>
                <span class="role-badge ${roleClass}">${currentUser.role}</span>
            </div>
            <button id="logoutBtn" class="btn btn-secondary">Sign Out</button>
        `;
        document.getElementById('logoutBtn').addEventListener('click', logout);
        if (currentUser.role === 'admin') {
            document.getElementById('addProductBtn').addEventListener('click', () => openProductForm());
            document.getElementById('manageUsersBtn').addEventListener('click', () => openUsersModal());
            document.getElementById('manageOptionsBtn').addEventListener('click', () => openOptionsModal());
        }
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
    
    // Helper function to check if a value matches any filter (handles comma-separated values)
    function matchesFilter(productValue, filterValues) {
        if (filterValues.length === 0) return true;
        if (!productValue) return false;
        
        // Split product value by comma and trim each part
        const productValues = productValue.split(',').map(v => v.trim());
        
        // Check if any of the product values match any of the filter values
        // Use partial matching: if filter value is contained in product value, it matches
        return productValues.some(pv => 
            filterValues.some(fv => 
                pv === fv || pv.includes(fv) || fv.includes(pv)
            )
        );
    }
    
    filteredProducts = allProducts.filter(p => {
        // Search filter
        const searchMatch = !searchTerm || 
            (p.short_desc && p.short_desc.toLowerCase().includes(searchTerm)) ||
            (p.long_desc && p.long_desc.toLowerCase().includes(searchTerm)) ||
            (p.vendor && p.vendor.toLowerCase().includes(searchTerm)) ||
            (p.data_ID && p.data_ID.toLowerCase().includes(searchTerm));
        
        // Category filter (handles comma-separated values)
        const categoryMatch = matchesFilter(p.datatype, currentFilters.categories);
        
        // Status filter (handles comma-separated values)
        const statusMatch = matchesFilter(p.status, currentFilters.statuses);
        
        // Stage filter (handles comma-separated values)
        const stageMatch = matchesFilter(p.stage, currentFilters.stages);
        
        // Region filter (handles comma-separated values)
        const regionMatch = matchesFilter(p.region, currentFilters.regions);
        
        // Vendor filter (handles comma-separated values)
        const vendorMatch = matchesFilter(p.vendor, currentFilters.vendors);
        
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
            // Check if clicking on "View Product" link or card
            if (e.target.classList.contains('view-link') || e.target.closest('.view-link')) {
                // Navigate to detail page
                window.location.href = `/dataset/${id}`;
            } else {
                // Show modal for quick view
                await showProductDetail(id);
            }
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
    const skipFields = ['id', 'short_desc', 'long_desc', 'data_ID'];
    
    // Build table rows for all fields
    const tableRows = Object.keys(product)
        .filter(key => !skipFields.includes(key))
        .map(field => {
            const isSensitive = sensitiveFields.includes(field);
            if (isSensitive && !isAdmin) return '';
            const label = field.replace(/_/g, ' ');
            const badge = isSensitive ? ' <span class="sensitive-badge">Admin</span>' : '';
            return `<tr><td class="field-name">${label}${badge}</td><td>${product[field] || 'N/A'}</td></tr>`;
        }).join('');
    
    const detailContent = document.getElementById('detailContent');
    detailContent.innerHTML = `
        <div class="detail-header">
            <div class="detail-title">${product.short_desc || product.data_ID}</div>
            <div class="detail-vendor">by ${product.vendor || 'Unknown'}</div>
            ${isAdmin ? `
            <div class="admin-actions">
                <button class="btn btn-primary" onclick="openProductForm(${product.id})">Edit</button>
                <button class="btn btn-danger" onclick="deleteProduct(${product.id})">Delete</button>
            </div>
            ` : ''}
        </div>
        <div class="detail-desc-section">
            <h3>Description</h3>
            <p>${product.long_desc || 'No description available.'}</p>
        </div>
        <table class="detail-table">
            <tbody>${tableRows}</tbody>
        </table>
    `;
    
    showModal('detailModal');
}

function showModal(id) {
    document.getElementById(id).classList.add('active');
}

function hideModal(id) {
    document.getElementById(id).classList.remove('active');
}

// CRUD Functions
async function openProductForm(id = null) {
    const form = document.getElementById('productForm');
    form.reset();
    
    // Remove ALL existing containers (both checkbox and tag) to prevent duplicates
    form.querySelectorAll('.checkbox-container, .tag-select-container').forEach(container => container.remove());
    
    // Show all selects (they might be hidden for multi-value)
    form.querySelectorAll('select').forEach(select => {
        select.style.display = '';
    });
    
    // Load column options and populate dropdowns
    const optionsRes = await fetch('/api/column-options');
    const options = await optionsRes.json();
    
    const dropdownColumns = ['asset_class', 'datatype', 'delivery_frequency', 'delivery_lag', 
                             'delivery_method', 'region', 'stage', 'status'];
    
    dropdownColumns.forEach(col => {
        const select = document.getElementById(`${col}-select`);
        if (select) {
            const isMulti = options[col]?.is_multi_value || false;
            
            // Remove any existing tag container for this column first
            const existingTagContainer = document.getElementById(`${col}-tags`);
            if (existingTagContainer) {
                existingTagContainer.remove();
            }
            
            if (isMulti) {
                // Create tag-based multi-select UI
                const container = select.parentElement;
                const tagContainer = document.createElement('div');
                tagContainer.className = 'tag-select-container';
                tagContainer.id = `${col}-tags`;
                
                if (options[col] && options[col].values) {
                    options[col].values.forEach(val => {
                        const tag = document.createElement('span');
                        tag.className = 'tag-select-option';
                        tag.dataset.value = val;
                        tag.textContent = val;
                        tag.addEventListener('click', () => {
                            tag.classList.toggle('selected');
                        });
                        tagContainer.appendChild(tag);
                    });
                }
                
                // Hide select and show tag container
                select.style.display = 'none';
                container.insertBefore(tagContainer, select.nextSibling);
                const hint = container.querySelector('.form-hint-multi');
                if (hint) hint.style.display = 'none';
            } else {
                // Single select - keep as dropdown
                select.removeAttribute('multiple');
                select.removeAttribute('size');
                select.innerHTML = '';
                const defaultOpt = document.createElement('option');
                defaultOpt.value = '';
                defaultOpt.textContent = '-- Select --';
                select.appendChild(defaultOpt);
                
                if (options[col] && options[col].values) {
                    options[col].values.forEach(val => {
                        const option = document.createElement('option');
                        option.value = val;
                        option.textContent = val;
                        select.appendChild(option);
                    });
                }
                
                const hint = select.parentElement.querySelector('.form-hint-multi');
                if (hint) hint.style.display = 'none';
            }
        }
    });
    
    if (id) {
        document.getElementById('editModalTitle').textContent = 'Edit Dataset';
        const res = await fetch(`/api/products/${id}`);
        const product = await res.json();
        for (const [key, value] of Object.entries(product)) {
            const input = form.elements[key];
            if (input) {
                if (input.tagName === 'SELECT' && input.multiple) {
                    // Multi-select: split by comma and select each value
                    const values = value ? value.split(',').map(v => v.trim()).filter(v => v) : [];
                    Array.from(input.options).forEach(opt => {
                        opt.selected = values.includes(opt.value);
                    });
                } else if (input.tagName === 'SELECT') {
                    input.value = value || '';
                } else {
                    input.value = value || '';
                }
            }
            
            // Handle tag containers for multi-value fields
            const tagContainer = document.getElementById(`${key}-tags`);
            if (tagContainer) {
                const values = value ? value.split(',').map(v => v.trim()).filter(v => v) : [];
                tagContainer.querySelectorAll('.tag-select-option').forEach(tag => {
                    if (values.includes(tag.dataset.value)) {
                        tag.classList.add('selected');
                    }
                });
            }
        }
    } else {
        document.getElementById('editModalTitle').textContent = 'Add Dataset';
    }
    
    showModal('editModal');
}

async function saveProduct(e) {
    e.preventDefault();
    const form = document.getElementById('productForm');
    const formData = new FormData(form);
    const data = {};
    
    // Handle form data, joining multi-select values with commas
    for (const [key, value] of formData.entries()) {
        // Skip checkbox array inputs (handled separately)
        if (key.endsWith('[]')) continue;
        
        const input = form.elements[key];
        if (input && input.tagName === 'SELECT' && input.multiple) {
            // Multi-select: get all selected values and join with comma
            const selected = Array.from(input.selectedOptions).map(opt => opt.value);
            data[key] = selected.join(', ');
        } else {
            data[key] = value;
        }
    }
    
    // Handle tag containers for multi-value fields
    form.querySelectorAll('.tag-select-container').forEach(container => {
        const selectedTags = container.querySelectorAll('.tag-select-option.selected');
        if (selectedTags.length > 0) {
            const fieldName = container.id.replace('-tags', '');
            const values = Array.from(selectedTags).map(tag => tag.dataset.value);
            data[fieldName] = values.join(', ');
        }
    });
    
    const id = data.id;
    delete data.id;
    
    const url = id ? `/api/products/${id}` : '/api/products';
    const method = id ? 'PUT' : 'POST';
    
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    if (res.ok) {
        hideModal('editModal');
        hideModal('detailModal');
        await loadProducts();
        await loadFilters();
    } else {
        const err = await res.json();
        alert(err.error || 'Failed to save');
    }
}

async function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) return;
    
    const res = await fetch(`/api/products/${id}`, { method: 'DELETE' });
    if (res.ok) {
        hideModal('detailModal');
        await loadProducts();
        await loadFilters();
    } else {
        const err = await res.json();
        alert(err.error || 'Failed to delete');
    }
}

// Add form submit listener
document.getElementById('productForm').addEventListener('submit', saveProduct);

// User Management
async function openUsersModal() {
    await loadUsers();
    showModal('usersModal');
}

async function loadUsers() {
    const res = await fetch('/api/users');
    const users = await res.json();
    const tbody = document.querySelector('#usersTable tbody');
    tbody.innerHTML = users.map(u => `
        <tr>
            <td>${u.username}</td>
            <td><span class="role-badge ${u.role === 'admin' ? 'admin' : ''}">${u.role}</span></td>
            <td><button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id})">Delete</button></td>
        </tr>
    `).join('');
}

document.getElementById('createUserForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const res = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: document.getElementById('newUsername').value,
            password: document.getElementById('newPassword').value,
            role: document.getElementById('newRole').value
        })
    });
    if (res.ok) {
        document.getElementById('createUserForm').reset();
        await loadUsers();
    } else {
        const err = await res.json();
        alert(err.error);
    }
});

async function deleteUser(id) {
    if (!confirm('Delete this user?')) return;
    const res = await fetch(`/api/users/${id}`, { method: 'DELETE' });
    if (res.ok) {
        await loadUsers();
    } else {
        const err = await res.json();
        alert(err.error);
    }
}

// Column Options Management
let columnOptions = {};
let selectedColumn = null;

async function openOptionsModal() {
    await loadColumnOptions();
    showModal('optionsModal');
}

async function loadColumnOptions() {
    const res = await fetch('/api/column-options');
    columnOptions = await res.json();
    
    const columnList = document.getElementById('columnList');
    const columns = ['asset_class', 'datatype', 'delivery_frequency', 'delivery_lag', 
                     'delivery_method', 'region', 'stage', 'status'];
    columnList.innerHTML = columns.map(col => `
        <li class="column-item" data-column="${col}">${col.replace(/_/g, ' ')}</li>
    `).join('');
    
    columnList.querySelectorAll('.column-item').forEach(item => {
        item.addEventListener('click', () => selectColumn(item.dataset.column));
    });
}

function selectColumn(colName) {
    selectedColumn = colName;
    document.getElementById('selectedColumnName').textContent = colName.replace(/_/g, ' ');
    
    // Update active state
    document.querySelectorAll('.column-item').forEach(item => {
        item.classList.toggle('active', item.dataset.column === colName);
    });
    
    // Load options for this column
    const options = columnOptions[colName]?.values || [];
    const tbody = document.querySelector('#optionsTable tbody');
    tbody.innerHTML = options.map(val => {
        // Find option ID (we'll need to fetch full list)
        return `<tr><td>${val}</td><td><button class="btn btn-danger btn-sm" onclick="deleteOptionValue('${colName}', '${val}')">Delete</button></td></tr>`;
    }).join('');
}

async function deleteOptionValue(colName, value) {
    if (!confirm(`Delete "${value}"?`)) return;
    const res = await fetch('/api/column-options/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ column_name: colName, value: value })
    });
    if (res.ok) {
        await loadColumnOptions();
        if (selectedColumn) selectColumn(selectedColumn);
    } else {
        const err = await res.json();
        alert(err.error || 'Failed to delete');
    }
}

document.getElementById('addOptionForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedColumn) {
        alert('Please select a column first');
        return;
    }
    const value = document.getElementById('newOptionValue').value;
    const res = await fetch('/api/column-options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            column_name: selectedColumn,
            value: value,
            is_multi_value: false
        })
    });
    if (res.ok) {
        document.getElementById('newOptionValue').value = '';
        await loadColumnOptions();
        if (selectedColumn) selectColumn(selectedColumn);
    } else {
        const err = await res.json();
        alert(err.error || 'Failed to add option');
    }
});

