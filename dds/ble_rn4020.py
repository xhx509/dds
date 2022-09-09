from mat.ble.bluepy.rn4020_utils import utils_logger_is_rn4020


def ble_interact_rn4020(mac, info):
    if not utils_logger_is_rn4020(mac, info):
        return
