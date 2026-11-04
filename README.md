# 本地日历

一个只在本机运行的日历管理工具：用一句自然语言输入日程，由 OpenAI 兼容接口的模型解析出时间和内容，确认后写入本地 SQLite。

- 月历 + 当日日程 + 未来 14 天列表
- 自然语言输入，解析结果可编辑后再保存
- 支持一次解析多个日程
- 手动新增、编辑、删除
- 未配置 API Key 时自动使用本地规则解析
- 纯 Python 标准库实现，无需安装第三方依赖即可运行
- 支持打包成单文件 Windows exe

## 快速开始

### 方式一：源码运行

要求 Python 3.10+（开发环境为 3.12）。

双击 `start.bat`。它会用 `pythonw` 在后台启动，不保留终端窗口，并自动打开浏览器。

也可以手动运行：

```powershell
python app.py
```

### 方式二：运行 exe

执行 `build.bat` 构建，产物为 `dist\calendar.exe`。exe 为无控制台窗口模式，双击即可使用，首次启动会在同目录创建 `data\`。

### 启动与退出

- 启动后浏览器会自动打开 <http://127.0.0.1:8765>。
- 再次双击 `start.bat` 或 exe 不会重复启动服务，只会打开已有页面。
- 退出：页面右上角「设置」→「退出应用」。
- 无窗口模式启动失败时，错误会写入 `data\error.log` 并弹出提示框。

## 配置模型

点击右上角「本地解析」或「设置」：

| 字段 | 说明 | 示例 |
| --- | --- | --- |
| Base URL | OpenAI 兼容接口地址 | `https://api.deepseek.com/v1` |
| API Key | 服务商密钥 | `sk-...` |
| 模型名 | 模型标识 | `deepseek-chat` |

常见配置：

- DeepSeek：`https://api.deepseek.com/v1` + `deepseek-chat`
- OpenAI：`https://api.openai.com/v1` + `gpt-4o-mini`
- Ollama：`http://localhost:11434/v1` + `qwen2.5:7b`（Key 随便填一个非空值）

填好后点「测试连接」验证，再保存。保存后状态会变为「模型解析」。

> API Key 以明文保存在本机 `data/config.json`，界面只显示掩码。请勿把 `data/` 目录分享或提交到版本库。

## 使用方式

在顶部输入框输入，例如：

- `明天下午 3 点和张总开会，地点 3 楼会议室`
- `下周一上午 10 点项目评审`
- `3 天后交季度报告`
- `今晚 8 点看电影`
- `明天全天团建`

点「解析日程」后会出现结果卡片：

- 点「编辑」可以修改标题、开始/结束时间、全天、地点、备注
- 点「添加」保存单条
- 点「全部添加」批量保存

也可以点日历中的日期后，用右侧「＋」手动添加。

## 本地规则解析

没有配置 API Key，或模型调用失败时，会使用内置规则解析，支持：

- 日期：今天/明天/后天/大后天、本周五/下周一、11 月 6 日、5 号、3 天后
- 时间：上午/下午/晚上 3 点、15:30、9 点半、2 小时后
- 全天事件、持续时长、`地点 xxx`

本地解析只作为兜底，复杂表达建议配置模型。

## 数据与隐私

- 数据库：`data/calendar.db`（SQLite）
- 配置：`data/config.json`
- 服务只监听 `127.0.0.1`，局域网无法访问
- 除调用你配置的模型接口外，不向任何第三方发送数据
- 备份日历只需复制 `data/calendar.db`

## 项目结构

```text
calendar/
├─ app.py                 启动入口
├─ calendar_app/
│  ├─ server.py           HTTP 服务与 API 路由
│  ├─ store.py            SQLite 存储
│  ├─ llm.py              OpenAI 兼容接口调用
│  ├─ parser.py           本地规则解析
│  ├─ config.py           配置读写
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

## 开发

```powershell
python -m unittest discover -s tests -v
python app.py
```

环境变量：

- `CALENDAR_PORT`：指定端口（默认 8765，占用时自动顺延）
- `CALENDAR_NO_BROWSER=1`：启动时不自动打开浏览器

## HTTP API

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
