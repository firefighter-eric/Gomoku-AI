# WebUI 架构与部署

生产地址：[gomoku-ai-brown.vercel.app](https://gomoku-ai-brown.vercel.app/)

## 产品范围

WebUI 是一个不依赖 Python 服务端的静态应用，支持：

- 人机对战。
- 同一设备双人对战，黑白双方轮流落子。
- AI 对 AI 自动对弈。
- 悔棋、重开、难度调整、执子切换和最近着法记录。
- 桌面端与移动端响应式布局。

当前“双人对战”是同屏模式，不包含跨设备房间、账号、匹配或实时网络同步。

## 技术结构

```text
React UI / SVG 棋盘
        │
TypeScript reducer 与自由规则胜负判断
        │
Web Worker
        │
wasm-bindgen 封装
        │
Rust alpha-beta:v5 搜索内核
```

- React 负责界面和可访问交互，棋盘使用 SVG 绘制，保持任意分辨率清晰。
- TypeScript reducer 维护不可变对局状态，三个模式共用相同落子和胜负规则。
- AI 计算放在 Web Worker 中，避免搜索阻塞主线程。
- `web-wasm/` 只做浏览器数据转换，搜索逻辑复用根目录 Rust library。
- 如果 WASM 初始化失败，Worker 会回退到浏览器兼容算法，并把实际引擎状态反馈到界面。

## 本地开发

要求 Node.js `22.12+` 或 `24+`。首次安装：

```bash
cd web
npm install
```

启动开发服务器：

```bash
npm run dev
```

重新生成 WASM 并完成生产构建：

```bash
npm run build
```

这个命令还要求本机安装 Rust、`wasm32-unknown-unknown` target 和 `wasm-pack`。只验证已提交的 WASM 与前端构建时可运行：

```bash
npm run build:web
```

## 测试

```bash
cd web
npm run lint
npm test
npm run build
npm run test:e2e
```

Playwright 会分别用桌面 Chromium 和移动端 Pixel 5 视口检查关键交互。发布验证还应覆盖生产域名的实际 DOM、响应式尺寸、WASM 落子和控制台错误。

## Vercel

Vercel 项目设置：

- Root Directory：`web`
- Framework Preset：Vite
- Build Command：`npm run build:web`
- Output Directory：`dist`

浏览器需要的 `web/src/wasm/pkg/` 是经过本地 `npm run build` 验证的生产资产，会随源码提交。这样 Vercel 只需要 Node.js，不需要在每次部署时下载 Rust 工具链。修改根目录 Rust 搜索内核或 `web-wasm/` 后，必须重新运行完整构建并提交生成包。

部署完成后，至少验证：

1. 首页可渲染且没有控制台错误。
2. 人机模式落下一手后，AI 能返回一步且界面显示 `Rust · WebAssembly`。
3. 双人模式由黑棋、白棋轮流落子，AI 控件处于禁用状态。
4. 390px 宽移动端没有横向滚动，棋盘仍可操作。
5. 刷新页面后保留模式、执子和难度设置，但开始一盘新棋。
