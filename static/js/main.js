// AI Dev Assistant - Project Mode with Sidebar

let currentProject = null;
let currentTicket = null;
let eventSource = null;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    setupTooltips();
});

function initializeApp() {
    checkSetup();
    loadProjects();
}

// ═══════════════════════════════════════════════════════
// VIEWS & NAVIGATION
// ═══════════════════════════════════════════════════════

function showView(viewId) {
    document.querySelectorAll('.content-view').forEach(view => {
        view.classList.remove('active');
    });
    
    const view = document.getElementById(`view-${viewId}`);
    if (view) {
        view.classList.add('active');
    }
    
    // Update page title
    const titles = {
        'welcome': 'Welcome',
        'setup': 'System Setup',
        'project': currentProject ? currentProject.name : 'Project'
    };
    
    document.getElementById('page-title').textContent = titles[viewId] || viewId;
}

function showWelcome() {
    currentProject = null;
    showView('welcome');
    document.getElementById('tickets-section').style.display = 'none';
}

function showSetup() {
    showView('setup');
    checkSetup();
}

function showProject(project) {
    currentProject = project;
    showView('project');
    
    // Update project info
    const projectInfo = document.getElementById('project-info');
    projectInfo.style.display = 'block';
    document.getElementById('project-name').textContent = project.name;
    document.getElementById('project-description').textContent = project.description;
    
    if (project.repo_url) {
        const repoLink = document.getElementById('project-repo-link');
        repoLink.href = project.repo_url;
        repoLink.style.display = 'inline-flex';
    }
    
    // Show tickets section
    document.getElementById('tickets-section').style.display = 'block';
    loadProjectTickets(project.id);
    
    // Reset forms
    document.getElementById('ticket-form').style.display = 'block';
    document.getElementById('progress-card').style.display = 'none';
    document.getElementById('success-card').style.display = 'none';
}

// ═══════════════════════════════════════════════════════
// PROJECTS
// ═══════════════════════════════════════════════════════

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();
        
        if (!data.success) {
            console.error('Failed to load projects:', data.error);
            return;
        }
        
        const projectsList = document.getElementById('projects-list');
        
        if (data.projects.length === 0) {
            projectsList.innerHTML = `
                <div class="empty-state-small">
                    <p>No projects</p>
                    <button class="btn-link" onclick="openNewProjectModal()">Create one</button>
                </div>
            `;
            return;
        }
        
        projectsList.innerHTML = '';
        
        data.projects.forEach(project => {
            const item = document.createElement('div');
            item.className = 'project-item';
            if (currentProject && currentProject.id === project.id) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <div class="project-name">${project.name}</div>
                <div class="project-meta">${project.tickets.length} ticket(s)</div>
            `;
            
            item.onclick = () => {
                document.querySelectorAll('.project-item').forEach(p => p.classList.remove('active'));
                item.classList.add('active');
                showProject(project);
            };
            
            projectsList.appendChild(item);
        });
        
    } catch (error) {
        console.error('Failed to load projects:', error);
    }
}

async function createProject() {
    const name = document.getElementById('project-name-input').value.trim();
    const description = document.getElementById('project-description-input').value.trim();
    const createRepo = document.getElementById('create-repo-checkbox').checked;
    
    if (!name) {
        alert('Please enter a project name');
        return;
    }
    
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                description: description,
                create_github_repo: createRepo
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            alert('Failed to create project: ' + data.error);
            return;
        }
        
        closeNewProjectModal();
        await loadProjects();
        showProject(data.project);
        
    } catch (error) {
        alert('Error creating project: ' + error.message);
    }
}

// ═══════════════════════════════════════════════════════
// TICKETS
// ═══════════════════════════════════════════════════════

async function loadProjectTickets(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/tickets`);
        const data = await response.json();
        
        if (!data.success) {
            console.error('Failed to load tickets:', data.error);
            return;
        }
        
        const ticketsList = document.getElementById('tickets-list');
        
        if (data.tickets.length === 0) {
            ticketsList.innerHTML = `
                <div class="empty-state-small">
                    <p>No tickets yet</p>
                </div>
            `;
            return;
        }
        
        ticketsList.innerHTML = '';
        
        data.tickets.slice().reverse().forEach(ticket => {
            const item = document.createElement('div');
            item.className = 'ticket-item';
            
            // Prefer PR status over basic status
            let statusBadge = '';
            if (ticket.pr_status) {
                const prStatus = ticket.pr_status.status;
                const prLabel = ticket.pr_status.status_label;
                statusBadge = `<div class="pr-status ${prStatus}">${prLabel}</div>`;
            } else if (ticket.status) {
                statusBadge = `<div class="ticket-status ${ticket.status}">${ticket.status.replace('_', ' ')}</div>`;
            }
            
            item.innerHTML = `
                <div class="ticket-id">${ticket.ticket_id}</div>
                <div class="ticket-desc">${ticket.description}</div>
                ${statusBadge}
            `;
            
            if (ticket.pr_url) {
                item.onclick = () => window.open(ticket.pr_url, '_blank');
                item.style.cursor = 'pointer';
            }
            
            ticketsList.appendChild(item);
        });
        
    } catch (error) {
        console.error('Failed to load tickets:', error);
    }
}

function startNewTicket() {
    document.getElementById('ticket-form').style.display = 'block';
    document.getElementById('progress-card').style.display = 'none';
    document.getElementById('success-card').style.display = 'none';
    
    // Clear both fields
    document.getElementById('ticket-id').value = '';
    document.getElementById('description').value = '';
    
    // Clear progress log
    document.getElementById('steps-log').innerHTML = '';
}

// ═══════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════

function setupEventListeners() {
    // Ticket form
    document.getElementById('ticket-form').addEventListener('submit', handleTicketSubmit);
    
    // Example cards
    document.querySelectorAll('.example-card').forEach(card => {
        card.addEventListener('click', function() {
            document.getElementById('ticket-id').value = '';  // Leave empty for auto-generation
            document.getElementById('description').value = this.dataset.desc;
        });
    });
}

async function handleTicketSubmit(e) {
    e.preventDefault();
    
    if (!currentProject) {
        alert('Please select a project first');
        return;
    }
    
    const ticketId = document.getElementById('ticket-id').value.trim();  // Can be empty now!
    const description = document.getElementById('description').value.trim();
    
    if (!description) {
        alert('Please enter a description');
        return;
    }
    
    // Hide form, show progress
    document.getElementById('ticket-form').style.display = 'none';
    document.getElementById('progress-card').style.display = 'block';
    
    await generateCode(currentProject.id, ticketId, description);
}

// ═══════════════════════════════════════════════════════
// CODE GENERATION
// ═══════════════════════════════════════════════════════

async function generateCode(projectId, ticketId, description) {
    try {
        const response = await fetch('/api/ticket', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: projectId,
                ticket_id: ticketId,  // Can be empty string
                description: description
            })
        });
        
        if (!response.ok) {
            throw new Error('Generation request failed');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error);
        }
        
        // Use the ticket_id from response (may be auto-generated)
        const finalTicketId = data.ticket_id;
        
        // Show auto-generated ticket ID if applicable
        if (data.auto_generated) {
            const log = document.getElementById('steps-log');
            const item = document.createElement('div');
            item.className = 'step-log-item';
            item.textContent = `🎫 Generated ticket ID: ${finalTicketId}`;
            log.appendChild(item);
        }
        
        subscribeToProgress(finalTicketId, description);
        
    } catch (error) {
        alert('Error starting code generation: ' + error.message);
        startNewTicket();
    }
}

function subscribeToProgress(ticketId, description) {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource(`/api/status/${ticketId}`);
    
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.keepalive) return;
        
        // Update progress
        document.getElementById('progress-fill').style.width = data.progress + '%';
        document.getElementById('progress-percentage').textContent = data.progress + '%';
        document.getElementById('current-step').textContent = data.step;
        
        // Add to log
        const log = document.getElementById('steps-log');
        const item = document.createElement('div');
        item.className = 'step-log-item';
        item.textContent = data.step;
        log.appendChild(item);
        log.scrollTop = log.scrollHeight;
        
        // Handle completion
        if (data.complete) {
            eventSource.close();
            setTimeout(() => {
                showSuccess(ticketId, description, data.pr_url);
                loadProjectTickets(currentProject.id);
            }, 500);
        }
        
        // Handle errors
        if (data.error) {
            eventSource.close();
            alert('Error: ' + data.error);
            startNewTicket();
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('SSE Error:', error);
        eventSource.close();
        alert('Connection error occurred');
        startNewTicket();
    };
}

function showSuccess(ticketId, description, prUrl) {
    document.getElementById('progress-card').style.display = 'none';
    document.getElementById('success-card').style.display = 'block';
    
    document.getElementById('success-ticket').textContent = ticketId;
    document.getElementById('success-feature').textContent = description;
    
    if (prUrl) {
        const prSection = document.getElementById('pr-section');
        const prLink = document.getElementById('pr-link');
        const prBtn = document.getElementById('view-pr-btn');
        
        prSection.style.display = 'flex';
        prLink.href = prUrl;
        prBtn.style.display = 'inline-flex';
    }
}

// ═══════════════════════════════════════════════════════
// SETUP CHECK
// ═══════════════════════════════════════════════════════

async function checkSetup() {
    try {
        const response = await fetch('/api/check-setup');
        const data = await response.json();
        
        // Update items
        updateSetupItem('setup-git', data.status.git, 'Installed', 'Not found');
        updateSetupItem('setup-gh', data.status.gh, 'Authenticated', 'Not authenticated');
        updateSetupItem('setup-ollama', data.status.ollama, 'Running', 'Not running');
        updateSetupItem('setup-model', data.status.model, 'Downloaded', 'Not found');
        
        // Update header status
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        
        if (data.ready) {
            statusDot.classList.add('ready');
            statusText.textContent = 'System Ready';
            document.getElementById('generate-btn').disabled = false;
        } else {
            statusDot.classList.add('error');
            statusText.textContent = 'Setup Required';
            document.getElementById('generate-btn').disabled = true;
        }
        
    } catch (error) {
        console.error('Setup check failed:', error);
    }
}

function updateSetupItem(elementId, isOk, okText, errorText) {
    const element = document.getElementById(elementId);
    const statusSpan = element.querySelector('.setup-status');
    
    if (isOk) {
        element.classList.add('ready');
        element.classList.remove('error');
        statusSpan.textContent = okText;
    } else {
        element.classList.add('error');
        element.classList.remove('ready');
        statusSpan.textContent = errorText;
    }
}

// ═══════════════════════════════════════════════════════
// MODAL MANAGEMENT
// ═══════════════════════════════════════════════════════

function openNewProjectModal() {
    const modal = document.getElementById('new-project-modal');
    modal.classList.add('active');
    document.getElementById('project-name-input').value = '';
    document.getElementById('project-description-input').value = '';
    document.getElementById('create-repo-checkbox').checked = false;
}

function closeNewProjectModal() {
    const modal = document.getElementById('new-project-modal');
    modal.classList.remove('active');
}

// ═══════════════════════════════════════════════════════
// FILES MODAL
// ═══════════════════════════════════════════════════════

async function openFilesModal() {
    if (!currentProject) {
        alert('No project selected');
        return;
    }
    
    const modal = document.getElementById('files-modal');
    modal.classList.add('active');
    
    // Load files
    await loadProjectFiles(currentProject.id);
}

function closeFilesModal() {
    const modal = document.getElementById('files-modal');
    modal.classList.remove('active');
}

async function loadProjectFiles(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/files`);
        const data = await response.json();
        
        if (!data.success) {
            document.getElementById('files-list').innerHTML = `
                <div class="empty-state-small">
                    <p>${data.error}</p>
                </div>
            `;
            return;
        }
        
        // Display summary
        const summary = data.summary;
        document.getElementById('files-summary').innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; padding: 1rem; background: var(--color-background); border-radius: var(--radius-md);">
                <div>
                    <div style="font-size: 0.75rem; color: var(--color-text-secondary); margin-bottom: 0.25rem;">Total Files</div>
                    <div style="font-size: 1.5rem; font-weight: 600;">${summary.total_files}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--color-text-secondary); margin-bottom: 0.25rem;">Code Files</div>
                    <div style="font-size: 1.5rem; font-weight: 600;">${summary.code_files}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--color-text-secondary); margin-bottom: 0.25rem;">Lines of Code</div>
                    <div style="font-size: 1.5rem; font-weight: 600;">${summary.total_lines.toLocaleString()}</div>
                </div>
            </div>
        `;
        
        // Display files
        const filesList = document.getElementById('files-list');
        
        if (data.files.length === 0) {
            filesList.innerHTML = '<div class="empty-state-small"><p>No files found</p></div>';
            return;
        }
        
        // Group files by directory
        const filesByDir = {};
        data.files.forEach(file => {
            const parts = file.path.split('/');
            const dir = parts.length > 1 ? parts[0] : '/';
            if (!filesByDir[dir]) {
                filesByDir[dir] = [];
            }
            filesByDir[dir].push(file);
        });
        
        let html = '<div style="max-height: 400px; overflow-y: auto;">';
        
        Object.keys(filesByDir).sort().forEach(dir => {
            html += `
                <div style="margin-bottom: 1.5rem;">
                    <div style="font-weight: 600; font-size: 0.875rem; color: var(--color-text); margin-bottom: 0.5rem; padding: 0.5rem; background: var(--color-background); border-radius: var(--radius-sm);">
                        📁 ${dir}
                    </div>
                    <div style="padding-left: 1rem;">
            `;
            
            filesByDir[dir].forEach(file => {
                const fileName = file.path.split('/').pop();
                const sizeKB = (file.size / 1024).toFixed(1);
                const icon = file.is_code ? '📄' : '📋';
                
                html += `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; border-bottom: 1px solid var(--color-border);">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span>${icon}</span>
                            <span style="font-family: monospace; font-size: 0.8125rem;">${fileName}</span>
                        </div>
                        <div style="display: flex; gap: 1rem; font-size: 0.75rem; color: var(--color-text-secondary);">
                            ${file.lines > 0 ? `<span>${file.lines} lines</span>` : ''}
                            <span>${sizeKB} KB</span>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div>';
        });
        
        html += '</div>';
        filesList.innerHTML = html;
        
    } catch (error) {
        console.error('Failed to load files:', error);
        document.getElementById('files-list').innerHTML = `
            <div class="empty-state-small">
                <p>Error loading files: ${error.message}</p>
            </div>
        `;
    }
}

// ═══════════════════════════════════════════════════════
// TOOLTIPS
// ═══════════════════════════════════════════════════════

function setupTooltips() {
    const tooltip = document.getElementById('tooltip');
    let hideTimeout;
    
    document.querySelectorAll('.info-icon').forEach(icon => {
        icon.addEventListener('mouseenter', function(e) {
            clearTimeout(hideTimeout);
            
            const text = this.dataset.tooltip;
            tooltip.textContent = text;
            tooltip.classList.add('visible');
            
            // Position tooltip
            const rect = this.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();
            
            let left = rect.left + rect.width / 2 - tooltipRect.width / 2;
            let top = rect.top - tooltipRect.height - 8;
            
            // Adjust if off screen
            if (left < 10) left = 10;
            if (left + tooltipRect.width > window.innerWidth - 10) {
                left = window.innerWidth - tooltipRect.width - 10;
            }
            if (top < 10) {
                top = rect.bottom + 8;
            }
            
            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
        });
        
        icon.addEventListener('mouseleave', function() {
            hideTimeout = setTimeout(() => {
                tooltip.classList.remove('visible');
            }, 100);
        });
    });
}

// ═══════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
}
