from ha import _Base
from mqtt import MqttTopic, MqttSharedTopic


def _state_format(state):
    return 'on' if state else 'off'


class Switch(_Base):
    def __init__(self, switch_id, switch_name, switch_func=None, state_topic=None, mqtt=None, **kwargs):
        super().__init__(mqtt=mqtt, component_id=switch_id, component_name=switch_name, component_type='switch',
                         **kwargs)

        command_topic = MqttTopic(mqtt, self.topic_name('cmd'))
        self._switch_func = switch_func
        self._state = False

        self._add_to_config({
            'payload_on': 'on',
            'payload_off': 'off',
            'state_on': 'on',
            'state_off': 'off',
            'command_topic': command_topic.name(),
        })

        if state_topic is None:
            self._state_topic = MqttTopic(mqtt, self.topic_name('state'))
            self._add_to_config({
                'state_topic': self._state_topic.name()
            })
        else:
            assert type(state_topic) is MqttSharedTopic
            self._state_topic = state_topic
            self._add_to_config({
                'state_topic': self._state_topic.name(),
                'value_template': self._state_topic.add_entry(switch_id, lambda: _state_format(self._state)),
            })

        command_topic.subscribe(lambda new_state: self._receive_command(new_state))

    def _receive_command(self, new_state):
        self(new_state == 'on')

    def send_update(self):
        self._state_topic.publish(_state_format(self._state))

    def __call__(self, new_state):
        self._state = new_state
        self.send_update()
