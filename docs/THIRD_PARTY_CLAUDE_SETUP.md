# 第三方 Claude API 配置指南

本指南介绍如何配置各种第三方 Claude API 服务。

## 支持的第三方服务类型

### 1. 🇨🇳 国内 Claude API 中转服务

适用于国内无法直接访问 Anthropic 官方 API 的场景。

**常见中转服务商:**
- ClaudeAPI.cn
- API2D
- OpenAI-SB
- 其他提供 Claude API 代理的服务

**配置示例:**
```
API 提供商: 第三方 Claude API
Base URL: https://api.your-proxy.com/v1
API Key: sk-xxxxxxxxxxxxxxxxxxxxxxxx
模型: claude-3-5-sonnet-20241022
```

**注意事项:**
- 确保中转服务支持 OpenAI 格式的 function calling
- 检查服务是否支持你选择的 Claude 模型版本
- 测试连接和模型可用性后再使用

### 2. ☁️ AWS Bedrock Claude

AWS Bedrock 提供托管的 Claude 模型服务。

**前提条件:**
- AWS 账户
- 已在 Bedrock 中启用 Claude 模型访问权限
- 配置好 AWS credentials

**配置示例:**
```
API 提供商: 第三方 Claude API
Base URL: https://bedrock-runtime.{region}.amazonaws.com/v1
API Key: AWS_ACCESS_KEY_ID:AWS_SECRET_ACCESS_KEY
模型: anthropic.claude-3-sonnet-20240229-v1:0
```

**AWS 区域选择:**
- us-east-1 (弗吉尼亚北部)
- us-west-2 (俄勒冈)
- ap-southeast-1 (新加坡)
- eu-central-1 (法兰克福)

### 3. 🔧 自建 Claude API 代理

如果你有自己搭建的 Claude API 代理服务。

**配置示例:**
```
API 提供商: 第三方 Claude API
Base URL: http://localhost:8000/v1  # 或你的域名
API Key: your-custom-auth-token
模型: claude-3-5-sonnet-20241022
```

**代理服务要求:**
- 实现 OpenAI 兼容的 `/v1/chat/completions` 端点
- 支持 `tools` 参数（function calling）
- 返回 OpenAI 格式的响应
- 支持流式响应（可选，本系统不使用）

### 4. 🌍 其他 OpenAI 兼容的 Claude 服务

**配置模板:**
```
API 提供商: 第三方 Claude API
Base URL: https://api.example.com/v1
API Key: your-api-key
模型: claude-3-5-sonnet-20241022
```

## 模型名称对照表

| 官方模型名 | 说明 | 支持工具调用 |
|-----------|------|-------------|
| claude-3-5-sonnet-20241022 | Claude 3.5 Sonnet (最新) | ✅ |
| claude-3-5-haiku-20241022 | Claude 3.5 Haiku (快速) | ✅ |
| claude-3-opus-20240229 | Claude 3 Opus (最强) | ✅ |
| claude-3-sonnet-20240229 | Claude 3 Sonnet | ✅ |
| claude-3-haiku-20240307 | Claude 3 Haiku | ✅ |
| claude-3-7-sonnet-20250219 | Claude 3.7 Sonnet (如可用) | ✅ |

## 配置步骤

1. **访问 Web 界面**
   ```
   http://localhost:8080
   ```

2. **选择 API 提供商**
   - 在下拉菜单选择 "第三方 Claude API"

3. **填写 Base URL**
   - 输入你的第三方服务的完整 URL
   - 确保以 `/v1` 结尾（如果服务要求）

4. **输入 API Key**
   - 从第三方服务商获取的 API 密钥
   - 或自建服务的认证令牌

5. **选择模型**
   - 从下拉列表选择预设模型
   - 或手动输入模型名称

6. **测试连接**
   - 点击"测试连接"按钮
   - 等待模型验证完成

7. **保存配置**
   - 确认配置无误后保存

## 常见问题

### Q1: 模型验证失败

**可能原因:**
- Base URL 不正确
- API Key 无效或过期
- 模型名称错误
- 网络连接问题

**解决方法:**
```bash
# 测试 API 连接
curl -X POST https://your-api.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","messages":[{"role":"user","content":"Hi"}]}'
```

### Q2: 工具调用不支持

**错误信息:** "No endpoints found that support tool use"

**原因:** 第三方服务不支持 function calling

**解决方法:**
- 确认服务商支持 OpenAI tools 格式
- 切换到支持工具调用的服务
- 联系服务商确认功能支持

### Q3: 401 Unauthorized

**原因:** API Key 无效

**解决方法:**
- 检查 API Key 是否正确复制
- 确认 API Key 是否已激活
- 检查是否有额度限制

### Q4: 模型不存在

**错误信息:** "Model not found" 或 404

**原因:** 模型名称与服务不匹配

**解决方法:**
- 查看服务商的模型列表
- 使用服务商指定的模型名称
- 联系服务商获取正确的模型标识

## 安全建议

1. **API Key 保护**
   - 不要将 API Key 提交到版本控制
   - 使用环境变量存储敏感信息
   - 定期轮换 API Key

2. **网络安全**
   - 优先使用 HTTPS 连接
   - 如使用自建代理，配置好防火墙
   - 监控 API 调用日志

3. **成本控制**
   - 设置 API 调用限额
   - 监控使用量和费用
   - 选择合适的模型（Haiku 更便宜）

## 推荐配置

### 高性能配置（适合生产）
```
API 提供商: 第三方 Claude API
模型: claude-3-5-sonnet-20241022
Base URL: 你的高可用中转服务
```

### 经济型配置（开发测试）
```
API 提供商: 第三方 Claude API
模型: claude-3-5-haiku-20241022
Base URL: 你的中转服务
```

### 平衡型配置（日常使用）
```
API 提供商: OpenRouter
模型: anthropic/claude-3.5-sonnet
Base URL: https://openrouter.ai/api/v1
```

## 技术支持

如遇到配置问题:
1. 查看应用日志: 服务端控制台输出
2. 检查网络连接: `curl` 测试 API
3. 验证 API 格式: 确保 OpenAI 兼容
4. 联系服务商: 获取技术支持

## 更新日志

- 2025-10-22: 添加第三方 Claude API 支持
- 支持国内中转、AWS Bedrock、自建代理等多种场景
