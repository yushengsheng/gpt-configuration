# GPT / Codex 配置

此仓库保存手动安装的第三方技能，供其他电脑配置 Codex 使用。官方内置技能由 Codex 自行提供。

## 已收录技能

| 技能 | 本机快照 | 用途 | 使用依赖 |
| --- | --- | --- | --- |
| `archify` | 3.0.1 | 生成架构图、流程图、时序图等 | Node.js 18 或更新版本；预览和导出依赖按技能要求配置 |
| `opencli-browser` | 本机安装版本 | 通过 OpenCLI 操作 Chrome | OpenCLI、Chrome 和浏览器桥接扩展；运行 `opencli doctor` 检查 |

`skills/` 保存完整的技能目录，包括说明、脚本、资源和原有许可证。未收录官方内置技能、插件缓存、账号登录状态或凭据。

## 在其他电脑安装

1. 安装 Codex 和 Python 3，将本仓库克隆或下载到本机。
2. 在仓库目录执行：

   ```sh
   python3 install-skills.py
   ```

   Windows 可使用：

   ```powershell
   py -3 install-skills.py
   ```

3. 按上表配置技能依赖。若 Codex 未显示新技能，重新启动 Codex。

脚本默认复制到当前用户的 `~/.agents/skills/`，供不同项目使用。仅处理仓库收录的技能；同名技能内容一致时跳过，内容不同时停止，不会直接覆盖。

## 更新已安装技能

先拉取仓库最新版本，再执行：

```sh
git pull
python3 install-skills.py --force
```

`--force` 会将有变化的同名技能移到 `~/.agents/skills-backups/<时间>/` 后安装仓库版本。备份目录位于技能扫描目录之外，避免重复加载；其他技能不受影响。Windows 将 `python3` 换成 `py -3`。

本机技能更新后，需要将对应完整目录更新到仓库的 `skills/`，提交并推送；其他电脑再拉取并运行安装脚本。Git 不会自动同步用户技能目录。

说明文件可以共享，软件依赖、插件连接和账号授权需要在各电脑单独配置。这些目录用于本地 Codex，普通 ChatGPT 网页聊天不会直接读取本机目录。

技能目录结构和加载位置参考 [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)。
