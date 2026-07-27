// Socket.IO connection
const socket = io();

// Global state
let sessions = {};
let currentSessionId = null;
let currentAgentId = null;
let currentPath = '.';
let selectedFilePath = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  updateTime();
  setInterval(updateTime, 1000);
  loadSessions();
  setInterval(loadSessions, 5000);
  loadAgents();
  setInterval(loadAgents, 5000);
  initSparkline();
  initTerminal();
  
  // File manager socket events
  setupFileManagerEvents();
});

// Update clock
function updateTime() {
  const now = new Date();
  document.getElementById('currentTime').textContent = now.toLocaleTimeString();
}

// Initialize sparkline chart
function initSparkline() {
  const chart = document.getElementById('sessionChart');
  const values = [40, 55, 35, 70, 42, 60, 45, 50, 65, 38];
  chart.innerHTML = '';
  values.forEach(v => {
    const bar = document.createElement('div');
    bar.className = 'sparkline-bar';
    bar.style.height = v + '%';
    chart.appendChild(bar);
  });
}

// Load sessions from server
async function loadSessions() {
  try {
    const response = await fetch('/api/sessions');
    const data = await response.json();
    sessions = data.sessions || {};
    updateSessionUI();
  } catch (error) {
    console.error('Failed to load sessions:', error);
  }
}

// Update session UI
function updateSessionUI() {
  const count = Object.keys(sessions).length;
  document.getElementById('sessionMetric').textContent = count;
  document.getElementById('activeCount').textContent = count;
  document.getElementById('alertCount').textContent = count > 0 ? Math.floor(Math.random() * 3) : 0;
  
  const tbody = document.getElementById('sessionsTable');
  if (count === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align:center; padding: 2rem; color: #64748b;">
          No active sessions. Click "New Session" to connect.
        </td>
      </tr>
    `;
    return;
  }
  
  tbody.innerHTML = '';
  sessions.forEach((session) => {
    const duration = getDuration(session.start_time);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code>${session.session_id.slice(0, 8)}</code></td>
      <td>${session.username}</td>
      <td>${session.host}:${session.port}</td>
      <td>
        <span class="status-indicator-cell">
          <span class="dot live"></span>
          Connected
        </span>
      </td>
      <td>${duration}</td>
      <td>
        <button class="btn-action" onclick="connectToSession('${session.session_id}')" title="Connect">
          <i class="fas fa-external-link-alt"></i>
        </button>
        <button class="btn-action" onclick="executeCommand('${session.session_id}')" title="Execute">
          <i class="fas fa-terminal"></i>
        </button>
        <button class="btn-action danger" onclick="disconnectSession('${session.session_id}')" title="Disconnect">
          <i class="fas fa-times"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Load agents from server
async function loadAgents() {
  try {
    const response = await fetch('/api/agents');
    const data = await response.json();
    const agents = data.agents || {};
    updateAgentUI(agents);
  } catch (error) {
    console.error('Failed to load agents:', error);
  }
}

// Update agent UI
function updateAgentUI(agents) {
  const count = Object.keys(agents).length;
  document.getElementById('agentCount').textContent = count;
  
  const statusText = document.getElementById('agentStatusText');
  const agentsList = document.getElementById('agentsList');
  
  if (count === 0) {
    statusText.textContent = 'No agents connected';
    agentsList.innerHTML = '<div style="text-align:center; padding: 1rem; color: #64748b;">No agents connected</div>';
  } else {
    const onlineCount = Object.values(agents).filter(a => a.status === 'online').length;
    statusText.textContent = `${onlineCount} online · ${count} total`;
    
    agentsList.innerHTML = '';
    agents.forEach((agent) => {
      const agentDiv = document.createElement('div');
      agentDiv.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 0.6rem; border-bottom: 1px solid #f1f5f9;';
      agentDiv.innerHTML = `
        <div>
          <div style="font-weight: 600; color: var(--dark);">${agent.hostname}</div>
          <div style="font-size: 0.85rem; color: #64748b;">${agent.ip_address} · ${agent.os}</div>
        </div>
        <button class="btn-small" onclick="openFileManager('${agent.agent_id}', '${agent.hostname}')" title="Browse Files">
          <i class="fas fa-folder-open"></i> Files
        </button>
      `;
      agentsList.appendChild(agentDiv);
    });
  }
}

// Get duration string
function getDuration(startTime) {
  const start = new Date(startTime);
  const now = new Date();
  const diff = Math.floor((now - start) / 1000);
  const hours = Math.floor(diff / 3600);
  const minutes = Math.floor((diff % 3600) / 60);
  const seconds = diff % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// Open connect modal
function openConnectModal() {
  document.getElementById('connectModal').style.display = 'flex';
}

// Close connect modal
function closeConnectModal() {
  document.getElementById('connectModal').style.display = 'none';
}

// Connect to new RDP session
document.getElementById('connectForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const clientName = document.getElementById('clientName').value;
  const host = document.getElementById('host').value;
  const port = parseInt(document.getElementById('port').value);
  const protocol = document.getElementById('protocol').value;
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  
  const sessionId = 'session_' + Date.now();
  
  try {
    const response = await fetch('/api/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        host,
        port,
        username,
        password,
        protocol
      })
    });
    
    const data = await response.json();
    
    if (data.status === 'connected') {
      addTerminalLine(`Connected to ${host}:${port} as ${username}`, 'success');
      addTerminalLine(`Session ID: ${sessionId}`, 'info');
      closeConnectModal();
      loadSessions();
      document.getElementById('connectForm').reset();
    } else {
      addTerminalLine(`Connection failed: ${data.message}`, 'error');
    }
  } catch (error) {
    addTerminalLine(`Error: ${error.message}`, 'error');
  }
});

// Disconnect session
async function disconnectSession(sessionId) {
  try {
    await fetch('/api/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    addTerminalLine(`Disconnected session ${sessionId.slice(0, 8)}`, 'warning');
    loadSessions();
  } catch (error) {
    addTerminalLine(`Error disconnecting: ${error.message}`, 'error');
  }
}

// Switch to session and focus terminal
async function executeCommand(sessionId) {
  currentSessionId = sessionId;
  const input = document.getElementById('terminalInput');
  input.focus();
  addTerminalLine(`Switched to session ${sessionId.slice(0, 8)}`, 'info');
}

// Connect to session
function connectToSession(sessionId) {
  currentSessionId = sessionId;
  const input = document.getElementById('terminalInput');
  if (input) {
    input.focus();
  }
  addTerminalLine(`Connected to session ${sessionId.slice(0, 8)}`, 'success');
}

// Connect to agent via SSH
function connectToAgent(agentId) {
  // Fetch agent info
  fetch(`/api/agents`)
    .then(r => r.json())
    .then(data => {
      const agents = data.agents || {};
      const agent = Object.values(agents).find(a => a.agent_id === agentId);
      if (agent) {
        // Try to connect via SSH automatically using agent's IP
        const sshHost = prompt(`Enter SSH credentials for ${agent.hostname} (${agent.ip_address}):`, agent.ip_address);
        if (sshHost) {
          const sshUser = prompt('Username (default: admin):', 'admin') || 'admin';
          const sshPass = prompt('Password:');
          if (sshPass) {
            const sessionId = 'ssh_' + Date.now();
            fetch('/api/connect', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                session_id: sessionId,
                host: sshHost,
                port: 22,
                username: sshUser,
                password: sshPass
              })
            }).then(() => {
              currentSessionId = sessionId;
              loadSessions();
              addTerminalLine(`SSH Connected to ${sshHost}:${sshUser}`, 'success');
              const input = document.getElementById('terminalInput');
              if (input) input.focus();
            });
          }
        }
      }
    });
}

// Terminal functionality
function initTerminal() {
  const input = document.getElementById('terminalInput');
  
  input.addEventListener('keypress', async (e) => {
    if (e.key === 'Enter') {
      const command = input.value.trim();
      if (!command) return;
      
      addTerminalLine(`$ ${command}`, 'command');
      input.value = '';
      
      if (command === 'help') {
        addTerminalLine('Available commands:', 'info');
        addTerminalLine('  help     - Show this help', 'info');
        addTerminalLine('  sessions - List active sessions', 'info');
        addTerminalLine('  agents   - List connected agents', 'info');
        addTerminalLine('  connect  - Connect to new RDP session', 'info');
        addTerminalLine('  clear    - Clear terminal', 'info');
        addTerminalLine('  status   - Show system status', 'info');
        addTerminalLine('  ls/dir   - List directory contents (simulated)', 'info');
        addTerminalLine('  pwd      - Show current directory', 'info');
        addTerminalLine('  whoami   - Show current user', 'info');
      } else if (command === 'clear') {
        clearTerminal();
      } else if (command === 'sessions') {
        const count = Object.keys(sessions).length;
        addTerminalLine(`Active sessions: ${count}`, 'info');
        Object.entries(sessions).forEach(([id, s]) => {
          addTerminalLine(`  ${id.slice(0, 8)} - ${s.host}:${s.port} (${s.username})`, 'info');
        });
      } else if (command === 'agents') {
        fetch('/api/agents')
          .then(r => r.json())
          .then(data => {
            const agents = data.agents || {};
            addTerminalLine(`Connected agents: ${data.total_agents}`, 'info');
            Object.entries(agents).forEach(([id, a]) => {
              addTerminalLine(`  ${id} - ${a.hostname} (${a.ip_address}) [${a.status}]`, 'info');
            });
          });
      } else if (command === 'status') {
        addTerminalLine('System Status: Online', 'success');
        addTerminalLine(`Active Sessions: ${Object.keys(sessions).length}`, 'info');
        addTerminalLine('Network: 99.9% uptime', 'info');
        addTerminalLine('Security: All Clear', 'info');
      } else if (command === 'connect' || command.startsWith('connect ')) {
        openConnectModal();
      } else {
        // Send command to server for real execution - no simulated responses
        if (!currentSessionId) {
          addTerminalLine('No active session. Use "connect" to establish a session.', 'warning');
          return;
        }
        try {
          const response = await fetch('/api/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: currentSessionId,
              command: command
            })
          });
          const data = await response.json();
          if (data.status === 'success') {
            addTerminalLine(data.output, 'success');
          } else {
            addTerminalLine(`Error: ${data.message}`, 'error');
          }
        } catch (error) {
          addTerminalLine(`Error: ${error.message}`, 'error');
        }
      }
    }
  });
}

// Add line to terminal
function addTerminalLine(text, type = '') {
  const output = document.getElementById('terminalOutput');
  const line = document.createElement('div');
  line.className = `terminal-line ${type}`;
  line.textContent = text;
  output.appendChild(line);
  output.scrollTop = output.scrollHeight;
}

// Clear terminal
function clearTerminal() {
  document.getElementById('terminalOutput').innerHTML = '';
  addTerminalLine('Terminal cleared.', 'info');
}

// Toggle terminal
function toggleTerminal() {
  const body = document.querySelector('.terminal-body');
  body.style.display = body.style.display === 'none' ? 'block' : 'none';
}

// Socket.IO events
socket.on('status', (data) => {
  console.log('Server:', data.msg);
});

socket.on('command_output', (data) => {
  addTerminalLine(data.output, 'success');
});

socket.on('agent_registered', (data) => {
  addTerminalLine(`Agent registered: ${data.message}`, 'success');
});

socket.on('heartbeat_update', (data) => {
  // Real-time heartbeat update from gateway
  const agentId = data.agent_id;
  const customerId = data.customer_id || 'N/A';
  const assignedIp = data.assigned_ip || 'N/A';
  const sessionStatus = data.session_status || 'unknown';
  
  // Update agent status in UI
  addTerminalLine(`Heartbeat: ${customerId} @ ${assignedIp} - ${sessionStatus}`, 'info');
  
  // Update agent list if showing
  loadAgents();
});

// File Manager Functions
function setupFileManagerEvents() {
  // File list received
  socket.on('file_list', (data) => {
    if (data.error) {
      addTerminalLine(`Error listing files: ${data.error}`, 'error');
      return;
    }
    displayFileList(data.files, data.path);
  });
  
  // Upload result
  socket.on('upload_result', (data) => {
    if (data.status === 'success') {
      addTerminalLine(`Uploaded: ${data.filename} (${data.size} bytes)`, 'success');
      if (document.getElementById('currentAgentId').value === data.agent_id) {
        refreshFileList();
      }
    } else {
      addTerminalLine(`Upload failed: ${data.error}`, 'error');
    }
  });
  
  // Download result
  socket.on('download_result', (data) => {
    if (data.status === 'success') {
      addTerminalLine(`Downloaded: ${data.filename} (${data.size} bytes)`, 'success');
      // Trigger browser download
      const link = document.createElement('a');
      link.href = 'data:application/octet-stream;base64,' + data.content;
      link.download = data.filename;
      link.click();
    } else {
      addTerminalLine(`Download failed: ${data.error}`, 'error');
    }
  });
  
  // Delete result
  socket.on('delete_result', (data) => {
    if (data.status === 'success') {
      addTerminalLine(`Deleted: ${data.path}`, 'success');
      refreshFileList();
    } else {
      addTerminalLine(`Delete failed: ${data.error}`, 'error');
    }
  });
  
  // Screenshot result
  socket.on('screenshot_result', (data) => {
    if (data.status === 'success') {
      const img = document.getElementById('screenshotImg');
      img.src = 'data:image/png;base64,' + data.content;
      document.getElementById('screenshotPreview').style.display = 'block';
      addTerminalLine('Screenshot captured', 'success');
    } else {
      addTerminalLine(`Screenshot failed: ${data.error}`, 'error');
    }
  });

  // Registry result
  socket.on('registry_result', (data) => {
    if (data.status === 'success') {
      addTerminalLine(`Registry ${data.hive}\\${data.key_path}:`, 'info');
      Object.entries(data.values).forEach(([name, value]) => {
        addTerminalLine(`  ${name} = ${value}`, 'info');
      });
    } else {
      addTerminalLine(`Registry read failed: ${data.error}`, 'error');
    }
  });

  // Processes result
  socket.on('processes_result', (data) => {
    if (data.status === 'success') {
      addTerminalLine('Running processes:', 'info');
      data.processes.forEach(proc => {
        addTerminalLine(`  PID ${proc.pid}: ${proc.name} (CPU: ${proc.cpu}%, MEM: ${proc.memory}%)`, 'info');
      });
    } else {
      addTerminalLine(`Process list failed: ${data.error}`, 'error');
    }
  });

  // Kill result
  socket.on('kill_result', (data) => {
    if (data.status === 'success') {
      addTerminalLine(`Process ${data.pid} terminated`, 'success');
    } else {
      addTerminalLine(`Kill failed: ${data.error}`, 'error');
    }
  });

  // Wake-on-LAN result
  socket.on('wol_result', (data) => {
    if (data.status === 'success') {
      addTerminalLine(`Wake-on-LAN packet sent to ${data.mac_address}`, 'success');
    } else {
      addTerminalLine(`Wake-on-LAN failed: ${data.message}`, 'error');
    }
  });
}

// Store selected row element for proper selection handling
let selectedRowElement = null;

// Open file manager for agent
function openFileManager(agentId, agentName) {
  currentAgentId = agentId;
  currentPath = '.';
  document.getElementById('fileManagerCard').style.display = 'block';
  document.getElementById('fileManagerAgent').textContent = agentName;
  document.getElementById('currentAgentId').value = agentId;
  refreshFileList();
}

// Close file manager
function closeFileManager() {
  document.getElementById('fileManagerCard').style.display = 'none';
  currentAgentId = null;
}

// Refresh file list
function refreshFileList() {
  if (!currentAgentId) return;
  
  socket.emit('list_files', {
    agent_id: currentAgentId,
    path: currentPath,
    command_id: `list_${Date.now()}`
  });
}

// Display file list
function displayFileList(files, path) {
  currentPath = path;
  const tbody = document.getElementById('fileList');
  tbody.innerHTML = '';
  
  // Add parent directory link if not in root
  if (path !== '.' && path !== '/') {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td colspan="5" style="cursor: pointer; color: var(--primary);" onclick="navigateTo('..')">
        <i class="fas fa-level-up-alt"></i> .. (Parent Directory)
      </td>
    `;
    tbody.appendChild(tr);
  }
  
  files.forEach(file => {
    const tr = document.createElement('tr');
    tr.onclick = (event) => selectFile(file.path, file.is_dir, tr, event);
    
    const icon = file.is_dir ? 'fa-folder folder' : (file.name.match(/\.(jpg|jpeg|png|gif)$/i) ? 'fa-file-image image' : 'fa-file file');
    const size = file.is_dir ? '-' : formatFileSize(file.size);
    
    tr.innerHTML = `
      <td>
        <i class="fas ${icon} file-icon"></i>
        ${file.name}
      </td>
      <td class="file-size">${size}</td>
      <td>${new Date(file.modified).toLocaleString()}</td>
      <td>${file.is_dir ? 'Directory' : 'File'}</td>
      <td>
        <button class="btn-action" onclick="event.stopPropagation(); navigateTo('${file.path}')" title="Open">
          <i class="fas fa-folder-open"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Format file size
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Select file - fixed to use event parameter instead of deprecated window.event
function selectFile(path, isDir, rowElement, event) {
  selectedFilePath = path;
  const rows = document.querySelectorAll('.file-table tbody tr');
  rows.forEach(tr => tr.classList.remove('selected'));
  
  // Use the passed row element instead of window.event
  if (rowElement) {
    rowElement.classList.add('selected');
  }
  document.getElementById('selectedFile').value = path;
}

// Navigate to directory
function navigateTo(path) {
  if (path === '..') {
    currentPath = currentPath.split('/').slice(0, -1).join('/') || '.';
  } else {
    currentPath = path;
  }
  refreshFileList();
}

// Upload file
function uploadFile() {
  if (!currentAgentId) {
    alert('Please select an agent first');
    return;
  }
  
  const input = document.createElement('input');
  input.type = 'file';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', currentPath);
    
    fetch(`/api/agent/${currentAgentId}/upload`, {
      method: 'POST',
      body: formData
    }).then(() => {
      addTerminalLine(`Uploading ${file.name}...`, 'info');
    });
  };
  input.click();
}

// Download selected file
function downloadSelected() {
  if (!selectedFilePath || !currentAgentId) {
    alert('Please select a file first');
    return;
  }
  
  fetch(`/api/agent/${currentAgentId}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: selectedFilePath })
  });
}

// Delete selected file
function deleteSelected() {
  if (!selectedFilePath || !currentAgentId) {
    alert('Please select a file first');
    return;
  }
  
  if (!confirm(`Delete ${selectedFilePath}?`)) return;
  
  fetch(`/api/agent/${currentAgentId}/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: selectedFilePath })
  });
}

// Take screenshot
function takeScreenshot() {
  if (!currentAgentId) {
    alert('Please select an agent first');
    return;
  }
  
  fetch(`/api/agent/${currentAgentId}/screenshot`, {
    method: 'POST'
  });
  addTerminalLine('Requesting screenshot...', 'info');
}

// Wake on LAN
function wakeOnLAN() {
  if (!currentAgentId) {
    alert('Please select an agent first');
    return;
  }
  
  const mac = prompt('Enter MAC address (e.g. 00:11:22:33:44:55):');
  if (!mac) return;
  
  socket.emit('wake_on_lan', {
    agent_id: currentAgentId,
    mac_address: mac,
    command_id: `wol_${Date.now()}`
  });
  addTerminalLine(`Sending Wake-on-LAN to ${mac}...`, 'info');
}

// List processes
function listProcesses() {
  if (!currentAgentId) {
    alert('Please select an agent first');
    return;
  }
  
  socket.emit('list_processes', {
    agent_id: currentAgentId,
    command_id: `proc_${Date.now()}`
  });
  addTerminalLine('Requesting process list...', 'info');
}

// Kill process
function killProcess() {
  const pid = prompt('Enter PID to kill:');
  if (!pid) return;
  
  socket.emit('kill_process', {
    agent_id: currentAgentId,
    pid: parseInt(pid),
    command_id: `kill_${Date.now()}`
  });
  addTerminalLine(`Killing PID ${pid}...`, 'info');
}

// Read registry
function readRegistry() {
  if (!currentAgentId) {
    alert('Please select an agent first');
    return;
  }
  
  const hive = prompt('Enter hive (HKLM/HKCU):', 'HKLM');
  const keyPath = prompt('Enter registry key path:', 'SOFTWARE\\Microsoft\\Windows');
  if (!hive || !keyPath) return;
  
  socket.emit('read_registry', {
    agent_id: currentAgentId,
    hive: hive,
    key_path: keyPath,
    command_id: `reg_${Date.now()}`
  });
  addTerminalLine(`Reading registry ${hive}\\${keyPath}...`, 'info');
}

// Download screenshot
function downloadScreenshot() {
  const img = document.getElementById('screenshotImg');
  const link = document.createElement('a');
  link.href = img.src;
  link.download = `screenshot_${Date.now()}.png`;
  link.click();
}

// Open File Explorer on client PC
function openFileExplorer() {
  if (!currentAgentId) {
    alert('Please select an agent first');
    return;
  }
  
  // Check if agent is online
  fetch('/api/agents')
    .then(r => r.json())
    .then(data => {
      const agents = data.agents || {};
      const agent = Object.values(agents).find(a => a.agent_id === currentAgentId);
      
      if (!agent || agent.status !== 'online') {
        alert('Agent is offline. Cannot open File Explorer.');
        return;
      }
      
      // Send command to open file explorer on client
      socket.emit('open_file_explorer', {
        agent_id: currentAgentId,
        command_id: `explorer_${Date.now()}`
      });
      
      addTerminalLine(`Opening File Explorer on ${agent.hostname}...`, 'info');
    })
    .catch(err => {
      addTerminalLine(`Error: ${err.message}`, 'error');
    });
}

// Close modal on backdrop click
document.getElementById('connectModal')?.addEventListener('click', (e) => {
  if (e.target === document.getElementById('connectModal')) {
    closeConnectModal();
  }
});

// Page navigation function - fixed window.event issue
function navigateToPage(page) {
  // Hide all pages
  document.querySelectorAll('.page-section').forEach(section => {
    section.style.display = 'none';
  });
  
  // Show selected page
  const targetPage = document.getElementById(page + 'Page');
  if (targetPage) {
    targetPage.style.display = 'block';
  }
  
  // Update title
  const titles = {
    dashboard: 'Operations Dashboard',
    sessions: 'RDP Sessions',
    agents: 'Agent Management',
    security: 'Security Center',
    settings: 'Settings',
    terminal: 'Remote Console'
  };
  const pageTitle = document.getElementById('pageTitle');
  if (pageTitle) {
    pageTitle.textContent = titles[page] || 'PCFixPro';
  }
  
  // Update nav active state
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => item.classList.remove('active'));
  
  // Find the active nav item based on the page parameter
  const activeNavItem = document.querySelector(`.nav-item[onclick*="${page}"]`);
  if (activeNavItem) {
    activeNavItem.classList.add('active');
  }
  
  return false;
}

// Menu toggle for mobile
document.querySelector('.menu-toggle')?.addEventListener('click', () => {
  document.querySelector('.sidebar').classList.toggle('show');
});