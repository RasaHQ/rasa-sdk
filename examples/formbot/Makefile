help:
	@echo "    train-core"
	@echo "        Train a dialogue model using Rasa core."
	@echo "    run"
	@echo "        Spin up a server that serves as an endpoint to receive facebook user messages."

train-core:
	python train_core.py -s data/stories.md -d domain.yml -o models/dialogue --epochs 1000 --debug --validation 0 --augmentation 0

run-core:
	python -m rasa_core.run --core models/dialogue --debug --endpoints endpoints.yml

run-actions:
	python -m rasa_core_sdk.endpoint --actions myactions

run:
	make run-actions&
	make run-core

visualize:
	python -m rasa_core.visualize -s data/stories.md -d domain.yml -o story_graph.png
