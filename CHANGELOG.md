# CHANGELOG

## 2026-10-30（接口核对）
- 核对 Codex `Stop` Hook 输入输出、插件 Hook 加载和信任要求
- 参考官方 `codex-plugin-cc` 的插件 Hook 目录结构
- 建立 `codex-auto-retry` 本地插件清单和 `Stop` Hook 配置
- 实现容量错误识别、指数退避、会话状态和重试次数上限
- 添加 5 项 Hook 单元测试及安装、限制说明
- 完成 JSON、Python 编译、单元测试和手工 Hook 输出验证
- 注册 `gpt-configuration-local` 本地市场并安装、启用 `codex-auto-retry`

## 2026-10-31（失败续跑）
- 记录 `PostModelRequest` 容量失败，让 `Stop` Hook 可处理空助手消息
- 刷新插件版本并补充重启客户端、会话范围说明
