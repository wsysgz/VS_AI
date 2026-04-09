# DeepSeek 配置手册

## 1. 申请 API Key

1. 打开 DeepSeek 平台。
2. 登录账号后创建 API Key。
3. 这个 Key 后面要同时填到本地 `.env` 和 GitHub Secrets 里。

## 2. 本地配置

把 `.env.example` 复制成 `.env`，然后填写：

- `DEEPSEEK_API_KEY`
- `AI_BASE_URL`
- `AI_MODEL`

默认推荐模型：

- `deepseek-chat`

## 3. GitHub 配置

进入你的 GitHub 仓库：

`Settings -> Secrets and variables -> Actions`

新增：

- `DEEPSEEK_API_KEY`
- `PUSHPLUS_TOKEN`

## 4. 本地验证

依赖安装完成后，执行：

```powershell
python -c "from auto_report.integrations.deepseek import build_deepseek_payload; print(build_deepseek_payload('hello')['model'])"
```

如果输出的是 `deepseek-chat`，说明本地配置链路已经正常。

## 5. 你后面实际要准备的东西

为了让这个项目真正启用 DeepSeek 分析，你至少要准备：

- 一个可用的 `DEEPSEEK_API_KEY`
- 本地 `.env` 配置
- GitHub Actions Secrets 配置

如果你还没申请 Key，可以先把框架跑起来，系统会自动回退到规则摘要模式，不会因为缺少 DeepSeek 而完全跑不动。
