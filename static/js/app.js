const API_BASE = '/api';

// 防抖函数
let modelValidationTimeout = null;

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

// 更新进度
function updateProgress(percent, text) {
    document.getElementById('progress-value').style.width = `${percent}%`;
    document.getElementById('progress-text').textContent = text;
}

// 开始生成
async function startGenerate() {
    const topic = document.getElementById('topic').value.trim();

    if (!topic) {
        showToast('请输入主题', 'error');
        return;
    }

    // 隐藏结果面板
    document.getElementById('result-panel').style.display = 'none';

    // 开始进度
    updateProgress(10, '开始生成内容...');

    try {
        const response = await fetch(`${API_BASE}/generate-and-publish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic })
        });

        // 模拟进度更新
        updateProgress(30, '正在检索相关信息...');
        await sleep(800);

        updateProgress(50, '正在生成文章内容...');
        await sleep(800);

        updateProgress(70, '正在优化内容...');
        await sleep(800);

        updateProgress(90, '正在发布到小红书...');

        const data = await response.json();

        if (data.success) {
            updateProgress(100, '发布成功！');
            await sleep(500);
            showResult(data.data);
            showToast('内容生成并发布成功', 'success');
        } else {
            updateProgress(0, '等待任务开始...');
            showToast(data.error || '生成失败', 'error');
        }
    } catch (error) {
        updateProgress(0, '等待任务开始...');
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