.PHONY: demo eval lint test

# 一条命令从零到出图(DFD):本地仿真回放,无外部依赖、无密钥、全合成信号
demo:
	python -m greenpulse.demo --config configs/default.yaml

# 五基线全家桶对照(R3.5):评测入口在缺任一基线时拒绝生成对照表
eval:
	python -m greenpulse.demo --config configs/default.yaml --all-baselines

lint:
	ruff check .

test:
	pytest
