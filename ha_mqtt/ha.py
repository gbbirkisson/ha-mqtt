import logging

from ha_mqtt.mqtt import MqttTopic

DISCOVERY_PREFIX = 'homeassistant'

ALLOWED_COMPONENT_TYPES = [
    'alarm_control_panel',
    'binary_sensor',
    'camera',
    'cover',
    'device_automation',
    'fan',
    'climate',
    'light',
    'lock',
    'sensor',
    'switch',
    'vacuum'
]


def _create_topic_name(component_type=None, node_id=None, component_id=None):
    assert component_type in ALLOWED_COMPONENT_TYPES, component_type + " is not allowed"
    assert component_id is not None, "component id cannot be None"

    return '{}/{}/{}/'.format(
        DISCOVERY_PREFIX,
        component_type,
        '{}/{}'.format(node_id, component_id) if node_id else component_id
    )


class Ha:

    def __init__(
            self,
            mqtt=None,
            component_type=None,
            node_id=None,
            component_id=None,
            auto_discovery=True,
    ):
        assert mqtt is not None, "mqtt cannot be None"

        self._mqtt = mqtt
        self._config = {}
        self._component_type = component_type
        self._node_id = node_id
        self._component_id = component_id
        self._auto_discovery = auto_discovery
        self._add_to_config({
            'unique_id': component_id
        })

    def subscribe(self, topic, func):
        self._mqtt.subscribe(topic, func)

    def publish(self, topic, message):
        self._mqtt.publish(topic, message)

    def topic_name(self, name):
        return _create_topic_name(component_type=self._component_type, node_id=self._node_id,
                                  component_id=self._component_id) + name

    def _add_to_config(self, d):
        self._config.update(d)

    def __enter__(self):
        if self._auto_discovery:
            assert self._config is not None, "component configuration cannot be none"
            logging.info('HASS adding component {}.{}'.format(self._component_type, self._component_id))
            self._mqtt.publish(self.topic_name('config'), self._config)
        return self

    def __exit__(self, *args):
        if self._auto_discovery:
            logging.info('HASS removing component {}.{}'.format(self._component_type, self._component_id))
            self._mqtt.publish(self.topic_name('config'), None)


class _Base(Ha):
    def __init__(
            self,
            component_name=None,
            icon=None,
            device_class=None,
            availability_topic=False,
            **kwargs
    ):
        super().__init__(**kwargs)

        self._component_name = component_name
        self._add_to_config({
            'name': component_name
        })

        self._icon = icon
        if icon is not None:
            self._add_to_config({
                'icon': icon
            })

        self._device_class = device_class
        if device_class is not None:
            self._add_to_config({
                'device_class': device_class
            })

        self._availability_topic = None
        if availability_topic:
            self._availability_topic = MqttTopic(kwargs['mqtt'], self.topic_name('available'))
            self._add_to_config({
                'availability_topic': self._availability_topic.name(),
                'payload_available': 'online',
                'payload_not_available': 'offline',
            })

    def available_set(self, available):
        if self._availability_topic is not None:
            self._availability_topic.publish('online' if available else 'offline')

    def get_id(self):
        return self._component_id

    def get_name(self):
        return self._component_name

    def get_icon(self):
        return self._icon

    def get_config(self):
        return self._config

    def on_connect(self):
        pass

    def send_update(self):
        pass
