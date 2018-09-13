from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rasa_core import utils
from rasa_core.agent import Agent
from rasa_core.policies.keras_policy import KerasPolicy
from rasa_core.policies.memoization import MemoizationPolicy
from rasa_core.policies.form_policy import FormPolicy

if __name__ == '__main__':
    utils.configure_colored_logging(loglevel="INFO")

    training_data_file = 'data/stories.md'
    model_path = 'models/dialogue'

    agent = Agent("domain.yml",
                  policies=[MemoizationPolicy(),
                            FormPolicy()])

    training_data = agent.load_data(training_data_file,
                                    augmentation_factor=0)

    agent.train(
            training_data,
            epochs=200,
            batch_size=10,
            validation_split=0.2
    )

    agent.persist(model_path)
