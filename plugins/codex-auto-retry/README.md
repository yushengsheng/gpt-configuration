# Codex Auto Retry

这是一个只在 Codex 运行时内工作的本地插件。它记录 `PostModelRequest` 的容量失败，并在 `Stop` Hook 中等待后自动生成有限次的继续提示，因此即使错误只出现在客户端错误卡片里、没有进入助手消息，也能尝试恢复。

## 安装

在仓库根目录执行：

```sh
codex plugin marketplace add ./plugins
codex plugin add codex-auto-retry@gpt-configuration-local
```

然后重启 Codex Desktop，并按客户端提示审查、信任该插件的 Hook。未信任前，Codex 会跳过插件 Hook。新建或继续一个 Codex 会话后，出现容量错误时插件会自动处理。

插件 Hook 由 Codex 提供 `PLUGIN_ROOT` 和 `PLUGIN_DATA`，不需要 macOS Accessibility、屏幕录制权限或系统级点击。

## 默认行为

- 只匹配明确的模型容量错误，例如 `Selected model is at capacity`。
- 每个会话回合最多自动继续 8 次。
- 等待间隔为 5、15、30、60 秒，之后沿用 60 秒。
- 状态保存在插件数据目录，超过 1 小时自动过期。
- 达到上限后停止并提示手动重试，避免无限循环。
- 插件安装或升级后需要重启 Codex Desktop，已打开的旧会话才会加载新的 Hook。

可通过插件运行环境覆盖：

```text
CODEX_AUTO_RETRY_MAX_ATTEMPTS=3
CODEX_AUTO_RETRY_DELAYS=10,30,60
```

## 本地验证

在仓库根目录运行：

```sh
python3 -m unittest discover -s plugins/codex-auto-retry/tests
```

## 限制

这是“自动继续”而不是模拟点击 Retry。插件只覆盖本地 Codex 会话；远程或云编排会话不运行本地命令 Hook。若当前客户端进程尚未重启，其他已打开会话也不会加载新 Hook。
