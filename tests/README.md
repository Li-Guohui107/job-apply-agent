# tests

`test_core.py` 检查这些行为：检索式、示例简历会被拒绝、模型多写的链接会被丢掉、同一职位不会重复记录、健康接口能响应。

在仓库根目录运行：

```bash
python -m unittest discover -s tests
```

这些测试不调用 DeepSeek，也不访问外网。
