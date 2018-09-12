help:
	@echo "    train-nlu"
	@echo "        Train the natural language understanding using Rasa NLU."
	@echo "    train-core"
	@echo "        Train a dialogue model using Rasa core."
	@echo "    run"
	@echo "        Spin up a server that serves as an endpoint to receive facebook user messages."

train-nlu:
	python -m rasa_nlu.train -c nlu_model_config.yml --fixed_model_name current \
	       --data ./data/nlu.md --path models/ --project nlu

train-core:
	python -m rasa_core.train -s data/stories.md -d domain.yml -o models/dialogue --epochs 1 --debug

run-core:
	python -m rasa_core.run --nlu models/nlu/current --core models/dialogue --debug --endpoints endpoints.yml

run-actions:
	python -m rasa_core_sdk.endpoint --actions myactions --slots myslots

run:
	make run-actions&
	make run-core

evaluate-nlu:
	python -m rasa_nlu.evaluate  --model models/nlu/current --data ./data/nlu.md

visualize:
	python -m rasa_core.visualize -s data/stories.md -d domain.yml -o story_graph.png
