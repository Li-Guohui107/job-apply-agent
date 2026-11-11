# app

这里是本机 Python 服务。

- `server.py` 提供页面和 JSON 接口。
- `search.py` 按城市和方向生成检索式，并读取公开结果。
- `analyze.py` 校验简历，整理匹配估计、计划和草稿。
- `chat.py` 回答问题。消息里没有城市时，不搜索全国。
- `llm.py` 调用 DeepSeek。钥匙只从环境变量读取。
- `store.py` 保存分析记录和已确认的投递包。简历正文不写进这些文件。
- `config.py` 负责路径，以及读取 `.env` 和 `.env.local`。

启动命令在仓库根目录执行：`python -m app`。
