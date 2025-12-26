# SRA已更新到 2.0
## Full Changelog：
- 更新日期：
- 版本：2.4
- 主要更新内容：
  - 货币战争支持刷开局 #74 #87
  - 货币战争支持超频博弈
  - SRA-cli 新增 '--log-level' 启动参数以设置日志级别, 支持 'TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL' 七个级别, 默认为 'TRACE'
- 功能调整：
  - `task run` 现在支持通过绝对路径加载任意位置的配置文件
  - 优化货币战争稳定性
- 问题修复：
  - 修复了历战余响中因获得光锥导致无法识别到战斗结束的问题 #72 #90