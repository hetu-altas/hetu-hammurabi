# DSH client-plugin 开发指南（dsh-client-plugin）

> 20260814 任务2（宪章看板DSH原生面板）登记。
> 本文记录 DSH web GUI 原生插件（client-plugin）的完整开发机制——
> 包结构、双面半区、注册流程、插槽挂载点、构建与加载规则，
> 以及本次实战踩坑结论。范例：`harness/dsh/hetu-dashboard/`（宪章看板原生面板）。

## 一、概念：双面插件（dual-face plugin）

DSH web 的浏览器插件（client-plugin）由**两个半区**组成，封装在一个 npm 包中：

| 半区 | 载体 | 职责 |
|------|------|------|
| **node 半区** | 包主入口（`main` → `lib/index.js`） | 普通 cordis 插件，可注册 webserver 路由、提供服务（如数据转发） |
| **browser 半区** | `exports["./client"]` → `lib/client.js` | 浏览器端模块：React 组件 + `ctx.slots.register` 注册 UI 插槽 |

包的 `package.json` 通过 `dsh.client` 元数据声明浏览器半区：

```jsonc
{
  "main": "lib/index.js",
  "exports": { ".": { "default": "./lib/index.js" }, "./client": { "default": "./lib/client.js" } },
  "dsh": { "client": { "inject": ["@deepseek-ai/dsh-client-runtime", "@deepseek-ai/dsh-client-ui-slots"], "platform": "web" } }
}
```

- `inject`：浏览器半区依赖的其他 client-plugin 包名（由 `dsh-client-modules` 组装进 `window.__DSH_BOOT__`）
- `platform: "web"`：仅 web 面生效

## 二、browser 半区产物形态

官方构建产物（由 apps/web 的 Vite 构建）为 `window.__ModuleLoader__.load({id, factory})` 包装的
UMD 模块，factory 内通过 `require(...)` 获取共享依赖（react、primitives 等），CSS 以
`data-plugin-css` style 标签注入：

```js
window.__ModuleLoader__.load({
  id: "@hetu/dsh-dashboard-panel/client",
  factory: (require) => {
    let react = require("react");
    // ... 组件与注册逻辑 ...
    exports.apply = apply;
    exports.inject = inject;
    return module.exports;
  }
});
```

**两种产出方式**：
1. **构建链**（官方）：克隆 deepseek-harness（monorepo，`packages/client/<name>/`），
   `pnpm install` + `pnpm run dev:web`（HMR）/ `pnpm run build`，产物含 `client.js`
2. **手写**（本任务采用，环境无源码/构建链）：直接按上述形态手写 `client.js`，
   用 `React.createElement` 写组件（无 JSX 编译），CSS 手动注入——`harness/dsh/hetu-dashboard/client.js` 即此形态

## 三、注册流程（把插件装进 web profile）

```bash
# 1. 包装入 dsh 安装目录（loader 的 import(name) 从安装目录解析包名！）
#    安装目录 = dsh CLI 所在 node_modules（npx 场景：~/.npm/_npx/<hash>/node_modules）
cp -r <pkg> <安装目录>/node_modules/@hetu/dsh-dashboard-panel/

# 2. web profile 的 cordis.patch.yml 追加 insert 行
#    - insert:
#      - id: hetu-dashboard
#        name: '@hetu/dsh-dashboard-panel'

# 3. 重启 dsh web 生效
```

**踩坑结论（loader 解析规则）**：
- patch `insert` 行的 `name` 若是**包名**，由 loader 的 `import(name)` 解析——解析上下文是
  **dsh 安装目录的 node_modules**，不是 profile 的 node_modules（profile 内 `npm install` 的包 loader 找不到！）
- **正解：用 bundle 机制注册**——包加进 profile `dsh.profile.bundles`（官方支持从 profile node_modules 解析），
  包内 `dsh.bundle.patch` 声明自身注册（与官方 dsh-web-app 包同构），不要在 profile patch 里手写 insert
- `name` 若是**绝对路径 .ts 文件**（如 dashboard-proxy 的挂法），loader 直接 import，无此问题

**踩坑结论（命令名必须小写）**：
- **`ctx.commands.register({name})` 的命令名必须全小写**：大写（如 `CC`）会导致
  normalizeDefinition 校验失败 → 插件激活失败 → **dsh web 服务直接起不来**
- 本命令名固定为 **`/cc`**（constitution coding），任何文档/提示词一律写小写 `/cc`

**踩坑结论（bundle 被 modules 静默跳过，启动无报错）**：
- **`exports` 必须包含 `"./package.json"`**：modules 用 `require.resolve('包名/package.json')` 定位包，
  包声明 exports 后未列出的子路径一律拒绝解析（`ERR_PACKAGE_PATH_NOT_EXPORTED`）→ resolveMeta 返回 null → 插件不进 client 图
- **`__ModuleLoader__.load({id})` 的 id 必须等于包名**：modules 校验注册 id === entry id（包名），
  否则浏览器端报 `loaded without registering "<包名>" via __ModuleLoader__.load`

## 四、UI 插槽挂载点（SlotMap）

插槽由 `dsh-client-ui-layout` / `dsh-client-ui-sidebar` 等包声明合并进 `SlotMap`，
`ctx.slots.register({name: '<slot key>', ...}, Component)` 注册组件。本面板用到的两个
**additive（list 型）挂载点**——不会替换现有 UI：

| 插槽 | kind | 用途 |
|------|------|------|
| `sidebar.footer.action` | list | 侧边栏底部操作按钮（设置旁），注册 `id` 即可共存 |
| `shell.overlay` | list | 全屏浮层（frame-wide floating layer），适合面板/弹层 |

注册代码形态（与 ui-workspace 官方一致）：

```js
function apply(ctx) {
  ctx.slots.inject("sidebar.footer.action", () => ctx.slots.register({
    name: "sidebar.footer.action", id: "hetu-dashboard", label: "宪章看板",
  }, DashboardButton));
}
```

list 型插槽必须带 `id`（`KindOptions`：list → `{id, order?, label?, priority?}`）。
其他插槽（single 型）会**替换**现有占用者，勿用于附加功能：`sidebar`（整列）、
`conversation`（中间列）、`details`（右侧列）、`sidebar.workspaces` / `sidebar.settings`。

## 五、数据通道（同源转发）

browser 半区不能直连外部端口（跨域），标准做法：**node 半区注册 webserver 前缀路由转发**。
本面板的数据通道由 `harness/dsh/plugins/dashboard-proxy.ts` 提供：

```
浏览器面板 fetch /api/hetu-dashboard/api/stats/overview
  → dashboard-proxy 剥前缀 → /api/stats/overview
  → 看板服务（127.0.0.1:8790，FastAPI）
```

降级契约：上游不可达时返回 `{"ok": false, "reason": "dashboard service unavailable"}`
（HTTP 200），面板统一渲染降级态。

## 五·五、一体化插件包（@hetu-altas/ConstitutionCoding-Plugin）

2026-08-15 起，/cc 命令、硬门禁（tools/pre-execute）、看板原生面板、流程状态栏整合为
**单一组合包** `plugins/constitution-coding/`（node 半区：command/gate/status-api；
client 半区：client.js），安装/卸载走官方 `npx @deepseek-ai/dsh plugin`：

```bash
npx @deepseek-ai/dsh plugin --profile web add ./plugins/constitution-coding
npx @deepseek-ai/dsh plugin --profile web remove @hetu-altas/ConstitutionCoding-Plugin
```

包内 cordis.patch.yml 注册 5 行：constitution-coding（node 入口，激活 client 半区）、
charter-command（/cc）、charter-gate（tools/pre-execute 硬门禁：危险命令/通知出口/日志门禁）、
charter-status-api（/dashboard + /api/hetu-dashboard 数据通道）、
dashboard-launcher（**看板服务自启钩子**：DSH 启动 1.5s 后探测 8790，未运行则自动拉起
uvicorn，detached 常驻、日志落 logs/hetu-altas/dashboard.log、幂等不重复启动）。
安装后 profile 不再需要任何手工 patch 条目。

宿主定位：三要件（constitution + harness/workflow.yaml + docs/资源地图.md）——
资源地图为宿主特有，避免把软链过 harness 组件的业务项目（hetu-aether 等）误判为宿主；
支持向上（宿主内启动）与向下（工作区根启动）双向探测。

### 包边界：什么在 npm 包里，什么留在仓库

| 组件 | 位置 | 说明 |
|------|------|------|
| 看板**原生面板**（浮层 + 总览/节点/门禁/任务/详情） | ✅ 包内 `client.js` | DSH GUI 侧，随 `npx @deepseek-ai/dsh plugin add` 安装即加载 |
| 右侧**流程状态栏** | ✅ 包内 `client.js` | 同上 |
| `/cc` 命令、硬门禁、数据通道、看板自启钩子 | ✅ 包内 `src/*.js` | node 半区 5 行注册 |
| 看板**数据服务**（FastAPI 后端 `harness/core/*.py` + 独立看板页 `harness/dashboard/`） | ⚠️ **仓库内** | Python 生态；同时承担 gate 判定 / seal-gate 落闸 / record 事件记录的 CLI 职责（模型按宿主绝对路径调用），不宜并入 npm 包 |
| 宪章 `constitution/`、流程定义 `workflow.yaml`、代理/技能 | ⚠️ **仓库内** | 与 DSH 解耦的单一权威（宪法不灭信条） |

**协作方式**：npm 包（DSH 侧 UI/门禁/命令）↔ Python 服务（数据/CLI）通过 `dashboard-launcher` 自动拉起 +
`/api/hetu-dashboard` 数据通道桥接。换机器部署需要**两条**：克隆仓库 + `npx @deepseek-ai/dsh plugin add ./plugins/constitution-coding`。

## 六、一键挂接

`scripts/attach_native_panel.sh` 把全部步骤固化为幂等脚本（含三要件校验，
把本指南的所有踩坑变成前置校验，不满足直接拒绝）：

```bash
bash scripts/attach_native_panel.sh            # 挂接（同步副本 + 注册 bundle + 校验配置树）
bash scripts/attach_native_panel.sh --check    # 只校验不写入
```

## 六·五、端口冲突（与 attu 等 Windows 应用）

**现象**：Windows 上打开 attu（监听 127.0.0.1:3080）却显示 DSH 界面——
WSL2 的 localhost 转发（wslrelay）会把 `localhost:3080` 请求转发到 WSL2 里先监听的 DSH。

**处理**：DSH 与 Windows 应用避免共用端口，启动时显式指定：

```bash
npx @deepseek-ai/dsh web --port 3090   # 或 npm exec @deepseek-ai/dsh -- web --port 3090（必须带 -- 分隔，否则 npm 把 --port 当自己的参数报错）   # DSH 换端口，attu 独占 3080
```

- attu → `http://localhost:3080`；DSH → `http://localhost:3090`
- 看板数据通道/原生面板/`/dashboard` 为 DSH 内部路由，自动跟随端口
- 排查命令（Windows PowerShell）：`netstat -ano | findstr LISTENING | findstr 3080`

## 七、验证命令

```bash
# 配置树是否含插件
dsh --profile web --dump-config | grep hetu

# client bundle 是否被 serve（重启后）
curl -s http://127.0.0.1:3080/plugins/@hetu/dsh-dashboard-panel/client.js | head

# boot manifest 是否注入（重启后）
curl -s http://127.0.0.1:3080/ | grep -o '__DSH_BOOT__[^<]*' | grep -c hetu

# 数据通道
curl -s http://127.0.0.1:3080/api/hetu-dashboard/api/stats/overview
```

## 八、遗留与后续

- 手写 client.js 无构建链/HMR：`pnpm run dev:web` 的 HMR 链需要 DSH 源码仓库（github 当前不可达），
  待网络可达后按 `harness/dsh/hetu-dashboard/src/` 的源码走官方构建链，即可获得热更新开发体验
- 可构建源码（等价的 React TSX）在 `harness/dsh/hetu-dashboard/src/client/`（规划中，任务3 补全）
