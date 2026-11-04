# Local Calendar / 本地日历

[English](#english) · [中文](#中文)

**Version:** v1.0.0 · **License:** MIT

A local-first calendar that turns natural-language text into events through an OpenAI-compatible model, stores everything in SQLite, and runs as a single Windows executable.

一个本地优先的日历工具：用自然语言输入日程，通过 OpenAI 兼容接口解析时间和内容，确认后写入本地 SQLite，并可打包为单文件 Windows exe。

---

## English

### Overview

Local Calendar is a single-user, local-only tool. The packaged exe starts a local server and opens the UI in your browser; all data stays on your machine. No account, no cloud sync, no telemetry.

### Features

- Month calendar, selected-day agenda, and a 14-day upcoming list
- Natural-language input with an editable preview before saving
- Parse multiple events from one sentence
- Manual create, edit, and delete
- Delete from the agenda list or directly from the edit dialog
- OpenAI-compatible model API (DeepSeek, OpenAI, Moonshot, local Ollama, etc.)
- Built-in rule-based parser for when no API key is configured
- SQLite storage in the system user-data directory
- Single-file, console-free Windows executable
- Single-instance launch: opening it again just reopens the page
- Responsive layout with light/dark mode
- Listen on `127.0.0.1` only

Not included in v1.0.0: recurring events, system notifications, remote/mobile access.

### Quick start

Requirements: Python 3.10+ (developed on 3.12).

#### Run from source

Double-click `start.bat`. It launches `pythonw` in the background, keeps no terminal window, and opens the browser automatically.

Or run manually:

```powershell
python app.py
```

#### Run the exe

```powershell
.\build.bat
```

The output is `dist\calendar.exe`. It runs without a console window. Runtime data is stored in the system user-data directory, not next to the exe.

#### Start and stop

- The app opens <http://127.0.0.1:8765>.
- Launching it again does not start a second server; it opens the existing page.
- To stop: open **Settings** in the top-right corner and click **Exit App**.
- If a windowed startup fails, the error is written to `%LOCALAPPDATA%\LocalCalendar\error.log` and shown in a message box.

### Model configuration

Click the status badge or **Settings** in the top-right corner.

| Field | Description | Example |
| --- | --- | --- |
| Base URL | OpenAI-compatible endpoint | `https://api.deepseek.com/v1` |
| API Key | Provider key | `sk-...` |
| Model | Model identifier | `deepseek-chat` |

Common configurations:

- DeepSeek: `https://api.deepseek.com/v1` + `deepseek-chat`
- OpenAI: `https://api.openai.com/v1` + `gpt-4o-mini`
- Ollama: `http://localhost:11434/v1` + `qwen2.5:7b` (any non-empty key)

Use **Test connection**, then **Save**. Without an API key, the app uses the built-in local parser.

> The API key is stored in plain text at `%LOCALAPPDATA%\LocalCalendar\config.json` on your own machine. It is never written into the project directory or the Git repository. The UI only shows a masked value.

### Usage

Enter a sentence in the input at the top, for example:

- `明天下午 3 点和张总开会，地点 3 楼会议室`
- `下周一上午 10 点项目评审`
- `3 天后交季度报告`
- `今晚 8 点看电影`
- `明天全天团建`

Then click **Parse**. The preview cards let you:

- **Edit** the title, start/end time, all-day flag, location, and notes
- **Add** a single event
- **Add all** parsed events at once

To delete an event:

- Hover an event in the agenda and click **Delete**, or
- Open the event and use **Delete Event** in the edit dialog

You can also select a day in the calendar and use the **+** button to add an event manually.

### Local fallback parser

When no API key is configured, or the model call fails, the app falls back to built-in rules:

- Dates: today/tomorrow/the day after, this/next weekday, `Nov 6`, `the 5th`, `in 3 days`
- Times: morning/afternoon/evening + hour, `15:30`, half past, `in 2 hours`
- All-day events, durations, and `location: ...`

The fallback is intentionally simple; use a model for complex expressions.

### Data and privacy

Runtime data is stored in the system user-data directory:

```text
Windows: %LOCALAPPDATA%\LocalCalendar\
├─ calendar.db    SQLite database
├─ config.json    model configuration (contains the API key)
└─ error.log      startup/runtime errors
```

- The server listens on `127.0.0.1` only.
- No data is sent anywhere except the model endpoint you configure.
- The project directory and Git repository never contain the database or API key.
- Existing data in the legacy project `data\` directory is migrated automatically on first launch.
- To back up, copy `%LOCALAPPDATA%\LocalCalendar\calendar.db`.
- Override the location with `CALENDAR_DATA_DIR`.

### Project structure

```text
calendar/
├─ app.py                 launcher
├─ calendar_app/
│  ├─ server.py           HTTP server and API routes
│  ├─ store.py            SQLite storage
│  ├─ llm.py              OpenAI-compatible API client
│  ├─ parser.py           local rule-based parser
│  ├─ config.py           configuration read/write
│  ├─ paths.py            system data directory and migration
│  └─ event_utils.py      validation and normalization
├─ static/
│  ├─ index.html          UI markup
│  ├─ styles.css          styles (light/dark)
│  ├─ app.js              frontend logic
│  └─ icon.ico            app icon
├─ tools/make_icon.py     icon generator
├─ tests/                 unit tests
├─ start.bat              source launcher
└─ build.bat              exe builder
```

### Development

```powershell
python -m unittest discover -s tests -v
python app.py
```

Environment variables:

- `CALENDAR_PORT`: port (default `8765`, falls back to the next free port)
- `CALENDAR_NO_BROWSER=1`: do not open a browser automatically
- `CALENDAR_DATA_DIR`: override the system data directory

### HTTP API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Health check |
| GET | `/api/config` | Read configuration (key masked) |
| PUT | `/api/config` | Save configuration |
| POST | `/api/config/test` | Test model connectivity |
| GET | `/api/events?start=&end=` | List events in a time range |
| POST | `/api/events` | Create an event |
| POST | `/api/events/bulk` | Create events in bulk |
| PATCH | `/api/events/{id}` | Update an event |
| DELETE | `/api/events/{id}` | Delete an event |
| POST | `/api/parse` | Parse text without saving |
| POST | `/api/shutdown` | Stop the local server |

### License

MIT. See [LICENSE](LICENSE).

---

## 中文

### 概述

本地日历是一个单用户、本地优先的桌面工具。界面通过浏览器或打包后的 exe 打开，所有数据都保存在本机。不需要账号，没有云同步，也没有遥测。

### 功能

- 月历、所选日期的日程列表、未来 14 天日程
- 自然语言输入，解析结果可编辑后再保存
- 一句话可解析多个日程
- 手动新增、编辑、删除
- 支持在日程列表中删除，也可在编辑弹窗中直接删除
- OpenAI 兼容接口（DeepSeek、OpenAI、Moonshot、本地 Ollama 等）
- 未配置 API Key 时使用内置规则解析
- SQLite 数据保存在系统盘的用户应用目录
- 单文件、无控制台窗口的 Windows exe
- 单实例启动：重复打开只会重新打开页面
- 响应式布局，支持浅色/深色模式
- 仅监听 `127.0.0.1`

v1.0.0 暂不包含：重复日程、系统提醒、远程/手机访问。

### 快速开始

要求 Python 3.10+（开发环境为 3.12）。

#### 源码运行

双击 `start.bat`。它会用 `pythonw` 在后台启动，不保留终端窗口，并自动打开浏览器。

也可以手动运行：

```powershell
python app.py
```

#### 运行 exe

```powershell
.\build.bat
```

产物为 `dist\calendar.exe`，无控制台窗口。运行时数据保存在系统盘的用户目录，不会在 exe 旁边生成 `data\`。

#### 启动与退出

- 启动后浏览器会自动打开 <http://127.0.0.1:8765>。
- 再次双击 `start.bat` 或 exe 不会重复启动服务，只会打开已有页面。
- 退出：页面右上角「设置」→「退出应用」。
- 无窗口模式启动失败时，错误会写入 `%LOCALAPPDATA%\LocalCalendar\error.log` 并弹出提示框。

### 配置模型

点击右上角的状态标签或「设置」。

| 字段 | 说明 | 示例 |
| --- | --- | --- |
| Base URL | OpenAI 兼容接口地址 | `https://api.deepseek.com/v1` |
| API Key | 服务商密钥 | `sk-...` |
| 模型名 | 模型标识 | `deepseek-chat` |

常见配置：

- DeepSeek：`https://api.deepseek.com/v1` + `deepseek-chat`
- OpenAI：`https://api.openai.com/v1` + `gpt-4o-mini`
- Ollama：`http://localhost:11434/v1` + `qwen2.5:7b`（Key 随便填一个非空值）

填好后点「测试连接」验证，再保存。未配置 API Key 时，应用会使用内置的本地规则解析。

> API Key 以明文保存在本机系统盘的 `%LOCALAPPDATA%\LocalCalendar\config.json`。项目目录和 Git 仓库中不包含该文件。界面只显示掩码。

### 使用方式

在顶部输入框输入，例如：

- `明天下午 3 点和张总开会，地点 3 楼会议室`
- `下周一上午 10 点项目评审`
- `3 天后交季度报告`
- `今晚 8 点看电影`
- `明天全天团建`

点「解析日程」后，结果卡片支持：

- **编辑**：修改标题、开始/结束时间、全天、地点、备注
- **添加**：保存单条
- **全部添加**：批量保存

删除日程：

- 在日程列表中悬停后点「删除」，或
- 打开日程，在编辑弹窗中点「删除日程」

也可以点日历中的日期后，用右侧「＋」手动添加。

### 本地规则解析

没有配置 API Key，或模型调用失败时，会使用内置规则解析，支持：

- 日期：今天/明天/后天/大后天、本周五/下周一、11 月 6 日、5 号、3 天后
- 时间：上午/下午/晚上 3 点、15:30、9 点半、2 小时后
- 全天事件、持续时长、`地点 xxx`

本地解析只作为兜底，复杂表达建议配置模型。

### 数据与隐私

运行时数据默认保存在系统盘的用户应用目录：

```text
Windows: %LOCALAPPDATA%\LocalCalendar\
├─ calendar.db    日历数据库
├─ config.json    模型配置（含 API Key）
└─ error.log      启动/运行错误日志
```

- 服务只监听 `127.0.0.1`，局域网无法访问
- 除调用你配置的模型接口外，不向任何第三方发送数据
- 项目目录和 Git 仓库不包含数据库与 API Key
- 旧版本放在项目 `data\` 目录的数据，首次启动时会自动迁移到系统目录
- 备份日历只需复制 `%LOCALAPPDATA%\LocalCalendar\calendar.db`
- 可用 `CALENDAR_DATA_DIR` 覆盖数据目录

### 项目结构

```text
calendar/
├─ app.py                 启动入口
├─ calendar_app/
│  ├─ server.py           HTTP 服务与 API 路由
│  ├─ store.py            SQLite 存储
│  ├─ llm.py              OpenAI 兼容接口调用
│  ├─ parser.py           本地规则解析
│  ├─ config.py           配置读写
│  ├─ paths.py            系统数据目录与旧数据迁移
│  └─ event_utils.py      数据校验与规范化
├─ static/
│  ├─ index.html          页面
│  ├─ styles.css          样式（支持深色模式）
│  ├─ app.js              前端逻辑
│  └─ icon.ico            应用图标
├─ tools/make_icon.py     图标生成脚本
├─ tests/                 单元测试
├─ start.bat              源码启动
└─ build.bat              打包 exe
```

### 开发

```powershell
python -m unittest discover -s tests -v
python app.py
```

环境变量：

- `CALENDAR_PORT`：指定端口（默认 8765，占用时自动顺延）
- `CALENDAR_NO_BROWSER=1`：启动时不自动打开浏览器
- `CALENDAR_DATA_DIR`：覆盖系统数据目录（默认 `%LOCALAPPDATA%\LocalCalendar`）

### HTTP API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/config` | 读取配置（Key 脱敏） |
| PUT | `/api/config` | 保存配置 |
| POST | `/api/config/test` | 测试模型连接 |
| GET | `/api/events?start=&end=` | 按范围查询日程 |
| POST | `/api/events` | 新增日程 |
| POST | `/api/events/bulk` | 批量新增 |
| PATCH | `/api/events/{id}` | 修改日程 |
| DELETE | `/api/events/{id}` | 删除日程 |
| POST | `/api/parse` | 自然语言解析（不落库） |
| POST | `/api/shutdown` | 停止本地服务 |

### 许可证

MIT，详见 [LICENSE](LICENSE)。
