import datetime

from mqtt import Mqtt
from sensor import Sensor, SettableSensor
from util import env


def create_average_sensor(sensor_name, unit_of_measurement, sensors, **kwargs):
    def _sensor():
        res = 0.0
        if len(sensors) == 0:
            return res
        for s in sensors:
            res = res + s()
        return res / len(sensors)

    return Sensor(sensor_name, unit_of_measurement, state_func=_sensor, **kwargs)


def create_weighted_average_sensor(sensor_name, unit_of_measurement, min_weight, max_weight,
                                   step_weight, initial_weight, sensors, **kwargs):
    k = kwargs

    if k.get('state_topic') is not None:
        state_topic = k.pop('state_topic')
    else:
        state_topic = None

    if k.get('icon') is not None:
        icon = k.pop('icon')
    else:
        icon = None

    pairs = []
    for s in sensors:
        weight = SettableSensor(s.get_name() + ' weight', '', min_weight, max_weight,
                                step_weight, initial_weight, icon='mdi:weight', **k)
        pairs.append((s, weight))

    def _sensor():
        values = [t() for t, w in pairs]
        weights = [w() for t, w in pairs]

        res = 0.0

        for x, y in zip(values, weights):
            res += x * y

        sum_weights = sum(weights)
        if sum_weights == 0:
            return sum(values) / len(values)

        return res / sum_weights

    k['state_topic'] = state_topic
    k['icon'] = icon
    return Sensor(sensor_name, unit_of_measurement, state_func=_sensor, **k), [w for t, w in pairs]


def create_last_update_sensor(sensor_name, **kwargs):
    def _sensor():
        return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    return Sensor(sensor_name, '', state_func=_sensor, icon='mdi:clock', device_class='timestamp', state_formatter_func=lambda s: s,
                  **kwargs)


def create_func_result_cache(func):
    old = [None]

    def w():
        res = func()
        if res is not None:
            old[0] = res
        return old[0]

    return w


def create_func_call_limiter():
    return _FuncCallLimiter()


class _FuncCallLimiter:
    def __init__(self):
        self._funcs = {}

    def wrap(self, f):
        self._funcs[f] = None

        def _w():
            if self._funcs[f] is None:
                self._funcs[f] = f()
            return self._funcs[f]

        return _w

    def clear(self):
        for f in self._funcs:
            self._funcs[f] = None
        return


def create_mqtt(mqtt_host=env('MQTT_HOST', 'homeassistant.local'), mqtt_username=env('MQTT_USER'),
                mqtt_password=env('MQTT_PASS')):
    return Mqtt(mqtt_host=mqtt_host, mqtt_username=mqtt_username, mqtt_password=mqtt_password)
