import logging
import time
from random import random

from climate import Climate
from mqtt import Mqtt, MqttSharedTopic
from registry import ComponentRegistry
from sensor import Sensor, ErrorSensor
from util import create_average_sensor, create_weighted_average_sensor, create_func_call_limiter, \
    create_func_result_cache

logging.basicConfig(level='DEBUG')


def climate_state_change(mode, target):
    print('Climate state changed! mode {}, target {}'.format(mode, target))


def create_temp_func(func_limiter, error_sensor):
    def _temp():
        if random() < 0.1:
            raise Exception()
        return random() * 100

    return func_limiter.wrap(create_func_result_cache(error_sensor.wrap_function(_temp)))


def create_components(mqtt):
    availability_topic = False
    auto_discovery = False

    registry = ComponentRegistry()

    state = MqttSharedTopic(mqtt, "/my/topic")
    registry.add_shared_topic(state)

    standard_config = {
        'mqtt': mqtt,
        'state_topic': state,
        'availability_topic': availability_topic,
        'auto_discovery': auto_discovery
    }

    errors = ErrorSensor('errors', 'errors', **standard_config)
    registry.add_component(errors)

    func_limiter = create_func_call_limiter()

    sen1 = Sensor('temp1', 'temp1', '°C', state_func=create_temp_func(func_limiter, errors), **standard_config)
    sen2 = Sensor('temp2', 'temp2', '°C', state_func=create_temp_func(func_limiter, errors), **standard_config)
    registry.add_component(sen1)
    registry.add_component(sen2)

    avg = create_average_sensor('avgtemp', 'avgtemp', '°C', [sen1, sen2], icon='mdi:thermometer-lines',
                                **standard_config)
    registry.add_component(avg)

    wavg, weights = create_weighted_average_sensor('wavgtemp', 'wavgtemp', '°C', 0, 200, 1, 100, [sen1, sen2],
                                                   icon='mdi:thermometer-lines', **standard_config)
    registry.add_component(wavg)
    for w in weights:
        registry.add_component(w)

    climate = Climate('climate', 'climate', wavg, state_change_func=climate_state_change, mqtt=mqtt,
                      availability_topic=availability_topic, auto_discovery=auto_discovery)
    registry.add_component(climate)

    if not auto_discovery:
        print("HA config:\n{}".format(registry.create_config()))

    return registry, func_limiter


if __name__ == "__main__":
    logging.info("Info")
    logging.error("error")
    logging.info("info")
    with Mqtt(mqtt_host='localhost') as mqtt:
        registry, func_limiter = create_components(mqtt)
        with registry:
            while True:
                registry.send_updates()
                time.sleep(1)
                func_limiter.clear()
