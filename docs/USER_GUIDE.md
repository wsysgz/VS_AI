# 用户操作手册

## 1. 这个项目能做什么

这个项目当前可以：

- 按计划定时生成 `AI / 大模型 / Agent` 快报
- 按计划定时生成 `AI × 电子信息` 快报
- 生成综合总报
- 把报告留档到本地 `data/` 目录
- 在 GitHub Actions 中执行并保存产物
- 通过 PushPlus 把摘要推送到手机

## 2. 本地运行

### 第一步：进入项目目录

项目根目录是：

`D:\GitHub\auto`

### 第二步：安装依赖

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

也可以直接运行：

```powershell
.\scripts\bootstrap.ps1
```

### 第三步：配置本地密钥

把 `.env.example` 复制为 `.env`，然后填写：

- `DEEPSEEK_API_KEY`
- `PUSHPLUS_TOKEN`
- `AI_MODEL`

如果你暂时还没有 DeepSeek Key，也可以先不填，系统会用规则摘要模式继续运行。

### 第四步：本地执行一次

```powershell
python -m auto_report.cli run-once
```

### 第五步：检查输出结果

重点看这些文件：

- `data/reports/latest-summary.md`
- `data/reports/latest-summary.json`
- `data/reports/latest-ai-llm-agent.md`
- `data/reports/latest-ai-x-electronics.md`
- `data/state/run-status.json`

## 3. 部署到 GitHub

### 第一步：创建 GitHub 仓库

在 GitHub 上新建一个仓库，然后把当前项目推上去。

### 第二步：配置 GitHub Actions Secrets

打开：

`仓库 Settings -> Secrets and variables -> Actions`

至少新增下面这些：

- `DEEPSEEK_API_KEY`

如果你希望手机收到推送，再额外新增：

- `PUSHPLUS_TOKEN`

说明：

- `DEEPSEEK_API_KEY` 建议配置，这样 GitHub 上生成的报告会带 AI 分析增强。
- `PUSHPLUS_TOKEN` 是可选项，不配置也能正常产出报告，只是不推送到手机。
- `GITHUB_TOKEN` 不需要手动新建，GitHub Actions 会自动提供默认值。

### 第三步：启用 GitHub Actions

进入仓库的 `Actions` 页面，如果 GitHub 提示确认，点击允许工作流运行。

### 第四步：手动触发第一次执行

打开工作流：

`Collect And Report`

点击：

`Run workflow`

后续只要你再向 `main` 分支推送代码，`Collect And Report` 也会自动执行一次，不需要每次手动点。

### 第五步：核对执行结果

检查这几项：

- 工作流日志是否成功结束
- 是否生成了名为 `auto-report-data` 的 artifact
- 仓库里的 `data/` 文件是否更新
- 如果配置了 `PUSHPLUS_TOKEN`，手机是否收到 PushPlus 推送

## 4. 手动补生成

如果你想手动补跑一轮，可以使用工作流：

`Backfill Report`

当前第一版的 `Backfill Report` 还是偏“重新渲染”模式，完整历史补跑会在下一批增强里继续补上。

## 5. 修改关注领域

如果你想调整领域关键词，修改：

- `config/domains/ai-llm-agent.yaml`
- `config/domains/ai-x-electronics.yaml`

如果你想增加或删减信息源，修改：

- `config/sources/rss.yaml`
- `config/sources/github.yaml`
- `config/sources/websites.yaml`
