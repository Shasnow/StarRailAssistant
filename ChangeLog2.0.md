### 主要更新内容:
- SRA-Server 新增 API Key 认证，保护服务器安全。

### 功能调整：
- 移除废弃的 `CurrencyWarsPolicy` 配置项。

### 问题修复：
- none

### 更新说明：

#### SRA-Server
- 新增基于密钥的认证机制：在 `appsettings.json` 中配置 `ApiKey` 后启用，未配置时允许匿名访问。
- 认证方式：请求头 `X-Api-Key: <your-key>`。
- 启动时若未配置 ApiKey，会打印警告日志 `ApiKey is not set; server is unsecured.`。
