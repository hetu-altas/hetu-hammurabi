# DeepSeek Harness 开发文档

> 本目录为 [DeepSeek Harness 开发文档](https://deepseek-harness.github.io/deepseek-harness/develop/basic/)（VitePress 中文站）的离线镜像，
> 2026-08-15 由 `scripts/fetch_dsh_docs.py` 批量抓取并转换为 Markdown。

## 目录索引（对应站点左侧导航）

### develop/basic（第一个插件）
| 页面 | 本地文件 |
|------|---------|
| 第一个插件 | [`develop/basic/index.md`](develop/basic/index.md) |
| 插件配置 | [`develop/basic/config.md`](develop/basic/config.md) |
| 发布插件 | [`develop/basic/publish.md`](develop/basic/publish.md) |
| 自定义工具 | [`develop/basic/tool.md`](develop/basic/tool.md) |

### develop/cordis-tutorial（Cordis 教程）
| 页面 | 本地文件 |
|------|---------|
| 教程索引 | [`develop/cordis-tutorial/index.md`](develop/cordis-tutorial/index.md) |
| 1. 编写第一个插件 | [`01-first-plugin.md`](develop/cordis-tutorial/01-first-plugin.md) |
| 2. 生命周期与副作用 | [`02-lifecycle-and-effects.md`](develop/cordis-tutorial/02-lifecycle-and-effects.md) |
| 3. 服务 | [`03-services.md`](develop/cordis-tutorial/03-services.md) |
| 4. 事件 | [`04-events.md`](develop/cordis-tutorial/04-events.md) |
| 5. 配置 | [`05-config.md`](develop/cordis-tutorial/05-config.md) |
| 6. 组合与 HMR | [`06-composition-and-hmr.md`](develop/cordis-tutorial/06-composition-and-hmr.md) |
| 7. 进入 Harness | [`07-into-the-harness.md`](develop/cordis-tutorial/07-into-the-harness.md) |

### develop/framework（框架）
| 页面 | 本地文件 |
|------|---------|
| 框架索引 | [`develop/framework/index.md`](develop/framework/index.md) |
| 事件系统 | [`develop/framework/events.md`](develop/framework/events.md) |
| 服务机制 | [`develop/framework/service.md`](develop/framework/service.md) |

### develop/practice（实践）
| 页面 | 本地文件 |
|------|---------|
| 实践索引 | [`develop/practice/index.md`](develop/practice/index.md) |
| LLM 适配器 | [`develop/practice/llm-adapter.md`](develop/practice/llm-adapter.md) |

### 其他
| 页面 | 本地文件 |
|------|---------|
| 快速开始（Web UI） | [`guide/quickstart.md`](guide/quickstart.md) |
| 站点首页 | 为 JS 渲染的 landing 页，无静态正文，见 [在线站点](https://deepseek-harness.github.io/deepseek-harness/) |

### reference（参考，61 页）
| 区 | 本地文件 |
|----|---------|
| 参考索引 | [`reference/index.md`](reference/index.md) |
| 生命周期/能力缝/配置目录/持久化目录/工具目录/工具执行管线 | `reference/{agent-lifecycle,capability-seams,config-catalog,persistence-catalog,tool-catalog,tool-execution-pipeline}.md` |
| cookbook（5 页） | `reference/cookbook/*.md`（extension-cookbook + adding-a-{tool,package,conversation-node,llm-adapter}） |
| cordis-api（6 页） | `reference/cordis-api/{context,events,fiber,inherited,registry,service}.md` |
| cordis-primer | `reference/cordis-primer.md` |
| subsystems（42 页） | `reference/subsystems/*.md`（approval/client-modules/commands/goal/jobs/llm-streaming/session/sandbox/skills/tools/web-server/workflow/workspace 等全量子系统） |

## 维护

- **重新抓取**：`<venv>/bin/python scripts/fetch_dsh_docs.py`（页面清单在脚本 `PAGES` 常量中）
- 转换说明：VitePress HTML → Markdown（标题/段落/代码块/表格/列表/链接），链接已转为绝对站点 URL 或保留相对路径
- 使用提示：教程内的 `tmp/cordis-tutorial` 等路径为站点原样内容，可按教程实际动手验证
