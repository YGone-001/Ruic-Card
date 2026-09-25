# RuiC Card · 个人全息卡片集

一个基于 [RuiC Card Skill](https://github.com/HRuiCcc/RuiC-card-skill) 制作的本地 3D 全息卡片项目。仓库包含四张可交互卡片、统一的 Three.js 展示站点、分层美术资产、GLB 模型和可编辑的 Blender 工程。

## 当前卡片

| 编号 | 名称 | 系列 | 项目目录 |
| --- | --- | --- | --- |
| 001 | 隙光 | 城市漫游 | `cards/brick-gap/` |
| 002 | 暮途 | 行车系列 | `cards/sunset-drive/` |
| 003 | 云阶 | 天游系列 | `cards/cloud-terrace/` |
| 004 | 夏荫 | 园游系列 | `cards/summer-shade/` |

四张卡使用同一目录契约：`assets/` 存放最终分层资产和 GLB 模型，`card-config.json` 存放卡片参数，`card.blend` 是可编辑工程。原始照片属于私密构建输入，不保存在仓库中。

## 快速预览

仓库已经提交打包后的 `web/app.bundle.js`，只需 Node.js，无需先安装 npm 包：

```powershell
node web/server.mjs
```

浏览器打开 <http://127.0.0.1:4173/>。服务默认只监听本机；在可信局域网中需要用手机预览时：

```powershell
$env:HOST = "0.0.0.0"
node web/server.mjs
```

可以通过查询参数直达卡片，例如 `?card=brick-gap`、`?card=sunset-drive`、`?card=cloud-terrace` 或 `?card=summer-shade`。

## 目录结构

```text
.
├── cards/
│   ├── brick-gap/                 # 001 隙光
│   ├── sunset-drive/              # 002 暮途
│   ├── cloud-terrace/             # 003 云阶
│   └── summer-shade/              # 004 夏荫
├── scripts/                       # 资产构建、流水线入口和验收脚本
├── tools/                         # Python 依赖清单；共享的便携版 Blender 缓存（gitignored）
├── web/
│   ├── assets/cards/<slug>/       # 展示站点所需的运行时资产
│   ├── cards/<slug>.json          # 展示站点卡片配置
│   ├── app.js                     # 前端源码
│   └── app.bundle.js              # 可直接运行的单文件 bundle
├── AGENTS.md                      # 自动化开发约定
└── README.md
```

## 开发环境

- Node.js 18+：运行本地服务和重新打包 Three.js 前端。
- Python 3.12：重建图层、执行图像处理和浏览器验收。
- Blender 4.5 LTS：重新生成 `.blend`/GLB；不纳入 Git，流水线可按需下载。
- RuiC Card Skill：提供通用卡片流水线。

安装前端开发依赖并重新打包：

```powershell
Set-Location web
npm install
npm run build
```

创建 Python 环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools\requirements-matting.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

仅处理文字图层时可使用较小的 `tools/requirements-typography.txt`。

## 流水线

`scripts/run_sunset_drive_pipeline.py` 和 `scripts/run_cloud_terrace_pipeline.py` 默认从 `~/.codex/skills/ruic-card-skill` 查找 RuiC Card Skill，也可显式指定：

```powershell
$env:RUIC_CARD_SKILL = "D:\path\to\RuiC-card-skill"
python scripts\run_cloud_terrace_pipeline.py
```

下载的 Blender 便携版会进入共享的 `tools/` 并被 `.gitignore` 排除。现有网页、GLB、Blender 工程和最终图层不依赖原始照片；只有重新生成图层时才需要在本机或私人存储中准备源素材，并设置对应环境变量：

| 卡片 | 私密构建输入 |
| --- | --- |
| `brick-gap` | `RUIC_BRICK_GAP_SOURCE_DIR` |
| `sunset-drive` | `RUIC_SUNSET_DRIVE_PHOTO`、`RUIC_SUNSET_DRIVE_BACKGROUND` |
| `cloud-terrace` | `RUIC_CLOUD_TERRACE_PHOTO` |
| `summer-shade` | `RUIC_SUMMER_SHADE_PHOTO` |

## 分支策略

- `main`：稳定基线，只接收经过验证的合并。
- `develop`：默认开发分支，日常修改先提交到这里。

## 仓库策略

仓库只保留直接预览和继续编辑所需的最终 PNG、GLB、配置及正式 `.blend` 文件。不得提交 `cards/*/source/` 中的原始照片或生成研究素材；卡片开发完成后应删除该目录，并从本机私密路径或私人云盘向构建脚本提供输入。此外不提交 Blender 便携版、虚拟环境、`node_modules`、渲染/验收输出、日志、`.blend1` 备份或每张卡重复生成的独立 Web 导出。
