import logging
from random import random

from climate import Climate
from components import create_func_result_cache, create_last_update_sensor, create_func_call_limiter, \
    create_average_sensor, create_weighted_average_sensor
from mqtt import Mqtt, MqttSharedTopic
from registry import ComponentRegistry
from sensor import Sensor, ErrorSensor
from util import setup_logging, sleep_for


def climate_state_change(mode, target):
    print('Climate state changed! mode {}, target {}'.format(mode, target))


def create_temp_func(func_limiter, error_sensor):
    def _temp():
        if random() < 0.1:
            raise Exception("Fake exception")
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

    errors = ErrorSensor('Errors', **standard_config)
    registry.add_component(errors)

    last_update = create_last_update_sensor('Last Update', **standard_config)
    registry.add_component(last_update)

    func_limiter = create_func_call_limiter()

    sen1 = Sensor('Temp 1', '°C', state_func=create_temp_func(func_limiter, errors), **standard_config)
    sen2 = Sensor('Temp 2', '°C', state_func=create_temp_func(func_limiter, errors), **standard_config)
    registry.add_component(sen1)
    registry.add_component(sen2)

    avg = create_average_sensor('Temp Average', '°C', [sen1, sen2], icon='mdi:thermometer-lines',
                                **standard_config)
    registry.add_component(avg)

    wavg, weights = create_weighted_average_sensor('Temp Weight Average', '°C', 0, 200, 1, 100, [sen1, sen2],
                                                   icon='mdi:thermometer-lines', **standard_config)
    registry.add_component(wavg)
    for w in weights:
        registry.add_component(w, send_updates=False)

    climate = Climate('Boiler', wavg, state_change_func=climate_state_change, mqtt=mqtt,
                      availability_topic=availability_topic, auto_discovery=auto_discovery)
    registry.add_component(climate)

    if not auto_discovery:
        logging.info("HA config:\n{}".format(registry.create_config()))

    return registry, func_limiter


if __name__ == "__main__":
    setup_logging()
    with Mqtt(mqtt_host='localhost') as mqtt:
        registry, func_limiter = create_components(mqtt)
        with registry:
            while True:
                registry.send_updates()
                sleep_for(1)
                func_limiter.clear()
