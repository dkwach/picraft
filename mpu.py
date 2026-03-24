import time
import sys

import smbus2 as smbus


class I2cBus:
    instance = None
    MRAA_I2C = 0

    def __init__(self, bus=None):
        if not I2cBus.instance:
            if bus is None:
                bus = self.get_bus()

            I2cBus.instance = smbus.SMBus(bus)
            self.bus = bus
            self.msg = smbus.i2c_msg

    @staticmethod
    def get_bus():
        try:
            import RPi.GPIO as GPIO

            # use the bus that matches your raspi version
            rev = GPIO.RPI_REVISION
        except Exception:
            rev = 3

        return 1 if rev == 2 or rev == 3 else 0

    def __getattr__(self, name):
        return getattr(self.instance, name)


class MPU9150:
    ADDRESS = 0x68
    REG_PWR_MGMT_1 = 0x6B

    ACCEL_XOUT = 0x3B
    ACCEL_YOUT = 0x3D
    ACCEL_ZOUT = 0x3F
    ACCEL_CONFIG = 0x1C

    TEMP_OUT = 0x41

    GYRO_XOUT = 0x43
    GYRO_YOUT = 0x45
    GYRO_ZOUT = 0x47
    GYRO_CONFIG = 0x1B

    MAXIMUM_SIGNED_WORD_VALUE = 0x7FFF
    ACCEL_RANGE_TO_FACTOR = {
        0: MAXIMUM_SIGNED_WORD_VALUE / 2,  # 2g
        1: MAXIMUM_SIGNED_WORD_VALUE / 4,  # 4g
        2: MAXIMUM_SIGNED_WORD_VALUE / 8,  # 8g
        3: MAXIMUM_SIGNED_WORD_VALUE / 16,  # 16g
    }

    GYRO_RANGE_TO_FACTOR = {
        0: 250,
        1: 500,
        2: 1000,
        3: 2000,
    }

    STANDARD_GRAVITY = 9.80665

    def __init__(self, bus_num=1, addr=ADDRESS):
        self.bus = I2cBus(bus_num)
        self.addr = addr
        self._accel_factor = None
        self._gyro_factor = None

        self._write(self.REG_PWR_MGMT_1, 0x00)
        self.update_accel_factor()
        self.update_gyro_factor()

    def update_accel_factor(self):
        accel_config = self.bus.read_byte_data(self.addr, self.ACCEL_CONFIG)
        afs_sel = (accel_config >> 3) & 0b11
        self._accel_factor = self.ACCEL_RANGE_TO_FACTOR[afs_sel]

    def update_gyro_factor(self):
        gyro_config = self.bus.read_byte_data(self.addr, self.GYRO_CONFIG)
        afs_sel = (gyro_config >> 3) & 0b11
        self._gyro_factor = self.GYRO_RANGE_TO_FACTOR[afs_sel]

    def get_temperature(self):
        return (self._read_word(self.TEMP_OUT) / 340.0) + 35

    def get_gyro(self):
        raw_gyro = (
            self._read_word(self.GYRO_XOUT),
            self._read_word(self.GYRO_YOUT),
            self._read_word(self.GYRO_ZOUT),
        )
        return [w / self._gyro_factor for w in raw_gyro]

    def get_accel(self):
        raw_accel = (
            self._read_word(self.ACCEL_XOUT),
            self._read_word(self.ACCEL_YOUT),
            self._read_word(self.ACCEL_ZOUT),
        )
        return [a / self._accel_factor * self.STANDARD_GRAVITY for a in raw_accel]

    def _write(self, register, value):
        self.bus.write_byte_data(self.addr, register, value)

    def _read_word(self, register):
        high = self.bus.read_byte_data(self.addr, register)
        low = self.bus.read_byte_data(self.addr, register + 1)

        raw = (high << 8) + low
        return -((65535 - raw) + 1) if raw >= 0x8000 else raw


def main():
    m = MPU9150()

    try:
        while True:
            print(
                "accel: {:5.2f}, {:5.2f}, {:5.2f}".format(*m.get_accel()),
                "gyro: {:5.2f}, {:5.2f}, {:5.2f}".format(*m.get_gyro()),
            )

            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
