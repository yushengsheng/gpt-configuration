# TODO

<!-- phase: 1 -->

- [x] 核对 Codex 官方 Hook 接口、插件打包规则和可复用开源实现
- [x] 建立本地 `codex-auto-retry` 插件目录与兼容清单
- [x] 实现带容量错误识别、退避、次数上限和状态持久化的 `Stop` Hook
- [x] 添加覆盖正常停止、容量错误、重试上限和 transcript 识别的测试
- [x] 补充安装、信任、配置和限制说明
- [x] 运行 JSON 校验、单元测试和手工 Hook 输入输出验证
- [x] 注册本地插件市场并安装、启用 `codex-auto-retry`
- [x] 用 `PostModelRequest` 记录容量失败，补齐无法从助手消息识别的场景
- [x] 刷新插件版本并验证安装缓存、测试和配置
