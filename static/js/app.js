const API_BASE = '/api';

// 防抖函数
let modelValidationTimeout = null;

// 任务管理 - 重新设计
let taskCardMap = {}; // { taskId: cardId } 映射任务ID到卡片ID

// 折叠面板
function togglePanel(panelId) {
    const panel = document.getElementById(`${panelId}-panel`);
    const toggle = document.getElementById(`${panelId}-toggle`);

    panel.classList.toggle('collapsed');
    toggle.classList.toggle('collapsed');
    toggle.textContent = panel.classList.contains('collapsed') ? '▶' : '▼';
}

// 验证模型是否可用
async function validateModel() {
    const apiKey = document.getElementById('llm_api_key').value.trim();
    const baseUrl = document.getElementById('openai_base_url').value.trim();
    const modelName = document.getElementById('default_model').value.trim();
    const statusEl = document.getElementById('model-validation-status');

    // 清空之前的状态
    statusEl.textContent = '';
    statusEl.className = 'validation-status';

    // 检查必填字段
    if (!apiKey || !baseUrl || !modelName) {
        return;
    }

    // 显示验证中状态
    statusEl.textContent = '验证中...';
    statusEl.className = 'validation-status validating';

    try {
        const response = await fetch(`${API_BASE}/validate-model`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                llm_api_key: apiKey,
                openai_base_url: baseUrl,
                model_name: modelName
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            statusEl.textContent = '✓ 模型可用';
            statusEl.className = 'validation-status valid';
        } else {
            statusEl.textContent = `✗ ${data.detail || '模型验证失败'}`;
            statusEl.className = 'validation-status invalid';
        }
    } catch (error) {
        statusEl.textContent = `✗ 验证失败: ${error.message}`;
        statusEl.className = 'validation-status invalid';
    }
}

// 防抖验证模型
function debounceValidateModel() {
    if (modelValidationTimeout) {
        clearTimeout(modelValidationTimeout);
    }
    modelValidationTimeout = setTimeout(validateModel, 800);
}

// 显示Toast消息
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// 保存配置
async function saveConfig() {
    const config = {
        llm_api_key: document.getElementById('llm_api_key').value.trim(),
        openai_base_url: document.getElementById('openai_base_url').value.trim(),
        default_model: document.getElementById('default_model').value,
        jina_api_key: document.getElementById('jina_api_key').value.trim(),
        tavily_api_key: document.getElementById('tavily_api_key').value.trim(),
        xhs_mcp_url: document.getElementById('xhs_mcp_url').value.trim()
    };

    if (!config.llm_api_key || !config.openai_base_url || !config.xhs_mcp_url) {
        showToast('请填写所有必填字段', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            showToast('配置保存成功', 'success');
        } else {
            showToast(data.error || '保存失败', 'error');
        }
    } catch (error) {
        showToast(`保存失败：${error.message}`, 'error');
    }
}

// 测试连接
async function testConnection() {
    const xhsMcpUrl = document.getElementById('xhs_mcp_url').value.trim();

    if (!xhsMcpUrl) {
        showToast('请先填写小红书MCP服务地址', 'error');
        return;
    }

    showToast('正在测试连接...', 'info');

    try {
        const response = await fetch(`${API_BASE}/test-login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ xhs_mcp_url: xhsMcpUrl })
        });

        const data = await response.json();

        if (data.success) {
            showToast('连接成功！', 'success');
        } else {
            showToast(data.error || '连接失败', 'error');
        }
    } catch (error) {
        showToast(`测试失败：${error.message}`, 'error');
    }
}

// 更新进度 - 支持任务ID参数
function updateProgress(taskIdOrPercent, percentOrText, textOrUndefined) {
    let taskId, percent, text;

    // 兼容旧的调用方式 updateProgress(percent, text)
    if (typeof taskIdOrPercent === 'number' && typeof percentOrText === 'string') {
        // 旧方式：updateProgress(10, '开始...')
        taskId = null;
        percent = taskIdOrPercent;
        text = percentOrText;
    } else {
        // 新方式：updateProgress(taskId, 10, '开始...')
        taskId = taskIdOrPercent;
        percent = percentOrText;
        text = textOrUndefined;
    }

    // 如果没有taskId，检查当前任务的taskId
    if (!taskId) {
        const currentTopicEl = document.getElementById('current-topic');
        taskId = currentTopicEl ? currentTopicEl.dataset.taskId : null;
    }

    // 更新当前任务显示（如果是当前任务）
    const currentTopicEl = document.getElementById('current-topic');
    if (currentTopicEl && currentTopicEl.dataset.taskId === taskId) {
        document.getElementById('progress-value').style.width = `${percent}%`;
        document.getElementById('progress-text').textContent = text;
    }

    // 更新历史卡片（如果任务在历史中）
    if (taskId && taskCardMap[taskId]) {
        const cardId = taskCardMap[taskId];
        const card = document.getElementById(cardId);
        if (card) {
            // 更新进度条
            const progressBar = card.querySelector('.task-card-progress-value');
            if (progressBar) {
                progressBar.style.width = `${percent}%`;
            }

            // 更新进度文字
            const progressText = card.querySelector('.task-card-progress-text');
            if (progressText) {
                progressText.textContent = text;
            }

            // 更新状态
            let status = 'running';
            let statusIcon = '⏳';
            if (percent === 100) {
                status = 'success';
                statusIcon = '✅';
            } else if (text.includes('失败') || text.includes('错误')) {
                status = 'error';
                statusIcon = '❌';
            }

            card.className = `task-card ${status}`;
            const statusEl = card.querySelector('.task-card-status');
            if (statusEl) {
                statusEl.textContent = statusIcon;
            }
        }
    }
}

// 将当前任务添加到历史
function moveCurrentToHistory() {
    const currentTopicEl = document.getElementById('current-topic');
    const currentTopic = currentTopicEl.textContent;
    const currentTaskId = currentTopicEl.dataset.taskId;
    const currentProgress = parseInt(document.getElementById('progress-value').style.width) || 0;
    const currentText = document.getElementById('progress-text').textContent;

    // 如果当前任务不是初始状态，才添加到历史
    if (currentTopic !== '等待任务开始...' && currentTaskId) {
        const historyPanel = document.getElementById('history-panel');
        const historyContainer = document.getElementById('task-history');

        // 显示历史面板
        historyPanel.style.display = 'block';

        // 判断状态
        let status = 'running';
        let statusIcon = '⏳';
        if (currentProgress === 100) {
            status = 'success';
            statusIcon = '✅';
        } else if (currentText.includes('失败') || currentText.includes('错误')) {
            status = 'error';
            statusIcon = '❌';
        }

        // 创建历史卡片，使用唯一ID
        const cardId = 'task-card-' + Date.now();
        const card = document.createElement('div');
        card.id = cardId;
        card.className = `task-card ${status}`;
        card.innerHTML = `
            <div class="task-card-header">
                <div class="task-card-topic" title="${currentTopic}">${currentTopic}</div>
                <div class="task-card-status">${statusIcon}</div>
            </div>
            <div class="task-card-progress">
                <div class="task-card-progress-bar">
                    <div class="task-card-progress-value" style="width: ${currentProgress}%"></div>
                </div>
                <div class="task-card-progress-text">${currentText}</div>
            </div>
        `;

        // 插入到最前面
        historyContainer.insertBefore(card, historyContainer.firstChild);

        // 建立任务ID到卡片ID的映射
        taskCardMap[currentTaskId] = cardId;

        // 自动滚动到历史面板
        setTimeout(() => {
            historyPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    }
}

// 开始生成 - 带任务ID追踪
async function startGenerate() {
    const topic = document.getElementById('topic').value.trim();

    if (!topic) {
        showToast('请输入主题', 'error');
        return;
    }

    // 创建新任务ID
    const taskId = 'task-' + Date.now();

    // 将当前任务移到历史
    moveCurrentToHistory();

    // 更新当前任务，保存任务ID
    const currentTopicEl = document.getElementById('current-topic');
    currentTopicEl.textContent = topic;
    currentTopicEl.dataset.taskId = taskId;

    // 清空输入框
    document.getElementById('topic').value = '';

    // 隐藏结果面板
    document.getElementById('result-panel').style.display = 'none';

    // 开始进度
    updateProgress(taskId, 10, '开始生成内容...');

    try {
        const response = await fetch(`${API_BASE}/generate-and-publish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic })
        });

        // 模拟进度更新
        updateProgress(taskId, 30, '正在检索相关信息...');
        await sleep(800);

        updateProgress(taskId, 50, '正在生成文章内容...');
        await sleep(800);

        updateProgress(taskId, 70, '正在优化内容...');
        await sleep(800);

        updateProgress(taskId, 90, '正在发布到小红书...');

        const data = await response.json();

        if (data.success) {
            updateProgress(taskId, 100, '发布成功！');
            await sleep(500);
            showResult(data.data);
            showToast('内容生成并发布成功', 'success');
        } else {
            updateProgress(taskId, 0, data.error || '生成失败');
            showToast(data.error || '生成失败', 'error');
        }
    } catch (error) {
        updateProgress(taskId, 0, `操作失败: ${error.message}`);
        showToast(`操作失败：${error.message}`, 'error');
    }
}

// 显示结果
function showResult(data) {
    const resultPanel = document.getElementById('result-panel');
    resultPanel.style.display = 'block';

    // 滚动到结果面板
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // 填充数据
    document.getElementById('result-title').textContent = data.title || '无标题';
    document.getElementById('result-content').textContent = data.content || '无内容';
    document.getElementById('result-time').textContent = data.publish_time || new Date().toLocaleString('zh-CN');

    // 标签
    const tagsEl = document.getElementById('result-tags');
    tagsEl.innerHTML = '';
    if (data.tags && data.tags.length > 0) {
        data.tags.forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'tag-item';
            tagEl.textContent = tag;
            tagsEl.appendChild(tagEl);
        });
    } else {
        tagsEl.textContent = '无标签';
    }

    // 图片
    const imagesEl = document.getElementById('result-images');
    imagesEl.innerHTML = '';
    if (data.images && data.images.length > 0) {
        data.images.forEach(url => {
            const imgEl = document.createElement('div');
            imgEl.className = 'img-item';
            imgEl.innerHTML = `
                <img src="${url}" alt="配图" onerror="this.style.display='none'">
                <a href="${url}" target="_blank" class="img-link">${url}</a>
            `;
            imagesEl.appendChild(imgEl);
        });
    } else {
        imagesEl.textContent = '无配图';
    }
}

// 辅助函数：延迟
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 快捷键：Ctrl/Cmd + Enter
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const topicInput = document.getElementById('topic');
        if (document.activeElement === topicInput) {
            startGenerate();
        }
    }
});

// 监听模型输入框的变化
document.addEventListener('DOMContentLoaded', () => {
    const modelInput = document.getElementById('default_model');
    const apiKeyInput = document.getElementById('llm_api_key');
    const baseUrlInput = document.getElementById('openai_base_url');

    if (modelInput) {
        modelInput.addEventListener('input', debounceValidateModel);
        apiKeyInput.addEventListener('input', debounceValidateModel);
        baseUrlInput.addEventListener('input', debounceValidateModel);
    }
});