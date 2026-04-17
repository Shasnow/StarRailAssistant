### 主要更新内容:
- n

### 功能调整：
- a

### 问题修复：
- 修复了在星际和平指南中点击差分宇宙前往参与时未直接进入差分宇宙界面导致无法进行差分宇宙任务的问题。

### 更新说明：
#### 即将到来的破坏性变更：
- 后端启动参数“run”和“single”将在未来版本中被移除，请尽快更新相关用法。
- 示例：
    - 旧用法：`run --config Default`
    - 新用法：`--execute "run Default"`
      -  或；`-e "run Default"`
    - 旧用法：`run --config Default --once`（仅运行一次后退出）
    - 新用法：`--execute "run Default & exit"`
      -  或：`-e "run Default & exit"`
- `--execute`与`-e`,`--command`,`-c`为相同的参数
