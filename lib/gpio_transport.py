# MicroPython imports
import sys
from machine import Pin
import utime as time

from transport import Transport

# ------------------------
# GPIO Parallel Interface
# ------------------------

DEBUG = False  # Set to True to enable debug logging of pin states and timing

class GPIO(Transport):
    """
    GPIO-based parallel transport base class.
    """

    MODE = None
    DATA_WIDTH = None

    def __init__(self, data_pins, valid_pin, ack_pin, timeout_ms, min_hold_time_ms):
        if self.MODE is None or self.DATA_WIDTH is None:
            raise ValueError("GPIO base class cannot be instantiated directly")

        if len(data_pins) != self.DATA_WIDTH:
            raise ValueError(
                "{} mode requires {} data pins".format(self.MODE, self.DATA_WIDTH)
            )

        self.mode = self.MODE
        self.data_pins = data_pins
        self.valid_pin = valid_pin
        self.ack_pin = ack_pin

        self.TIMEOUT_MS = timeout_ms  # Default timeout in milliseconds
        self.MIN_HOLD_TIME_MS = min_hold_time_ms

        # MicroPython Pin setup
        self._set_data_pins_input()

        self.read_buffer = bytearray()

    def _log_pin_states(self):
        """Log current states of data, VALID, and ACK pins for debugging"""
        data_states = [str(pin.value()) for pin in self.data]
        valid_state = str(self.valid.value())
        ack_state = str(self.ack.value())
        print("Valid ", self.valid)
        print("Ack   ", self.ack)
        print(
            f"DATA: {' '.join(data_states)} | VALID: {valid_state} | ACK: {ack_state}"
        )

    def _wait_until_valid_is(self, v):
        """Wait for VALID pin to reach specified value within timeout"""
        start = time.ticks_ms()
        while self.valid.value() != v:
            if self.TIMEOUT_MS != 0 and time.ticks_diff(time.ticks_ms(), start) > self.TIMEOUT_MS:
                raise RuntimeError(
                    "Timeout waiting for VALID signal to be {}".format(v)
                )
        return True

    def _wait_until_ack_is(self, v):
        """Wait for ACK pin to reach specified value within timeout"""
        start = time.ticks_ms()
        while self.ack.value() != v:
            if self.TIMEOUT_MS != 0 and time.ticks_diff(time.ticks_ms(), start) > self.TIMEOUT_MS:
                raise RuntimeError("Timeout waiting for ACK signal to be {}".format(v))
        return True

    def _set_data_pins_output(self):
        """Set data pins as outputs (for writing)"""
        self.data = [Pin(p, Pin.OUT) for p in self.data_pins]
        self.ack = Pin(self.ack_pin, Pin.IN, Pin.PULL_UP)
        self.valid = Pin(self.valid_pin, Pin.OUT)
        self.valid.value(0)

    def _set_data_pins_input(self):
        """Set data pins as inputs (for reading)"""
        self.data = [Pin(p, Pin.IN, Pin.PULL_UP) for p in self.data_pins]
        self.valid = Pin(self.valid_pin, Pin.IN, Pin.PULL_UP)
        self.ack = Pin(self.ack_pin, Pin.OUT)
        self.ack.value(0)

    def _write_byte(self, byte):
        """Write a single byte using the parallel interface."""
        raise NotImplementedError()

    def _write_nibble(self, nibble):
        """Write a 4-bit nibble"""
        self._set_data_pins_output()
        if DEBUG:
            print("Waiting for ACK low")
        self._wait_until_ack_is(0)

        if DEBUG:
            print("Writing nibble: ", nibble)

        for i, pin in enumerate(self.data):
            pin.value((nibble >> i) & 1)

        if DEBUG:
            print("setting VALID high")
        self.valid.value(1)
        if DEBUG:
            print("waiting for ACK high")
        self._wait_until_ack_is(1)
        if DEBUG:
            print("setting VALID low")
        self.valid.value(0)
        time.sleep_ms(self.MIN_HOLD_TIME_MS)  # Hold valid low long enough for slow client to see it

    def _read_byte(self):
        """Read a single byte from the parallel interface."""
        raise NotImplementedError()

    def _read_nibble(self):
        """Read a 4-bit nibble"""
        self._set_data_pins_input()

        # Resync: ensure we start only after VALID is low
        if not self._wait_until_valid_is(0):
            return None

        # Wait for VALID high
        if DEBUG:
            self._log_pin_states()
        if not self._wait_until_valid_is(1):
            return None
        if DEBUG:
            self._log_pin_states()

        # Small settle time for data lines
        # time.sleep_us(5)

        nibble = 0
        for i, pin in enumerate(self.data):
            if pin.value():
                nibble |= 1 << i

        if DEBUG:
            print("Read nibble:", nibble)
        self.ack.value(1)
        time.sleep_ms(self.MIN_HOLD_TIME_MS)  # Hold ACK high long enough for slow client to see it
        if DEBUG:
            self._log_pin_states()
        self._wait_until_valid_is(0)
        self.ack.value(0)
        time.sleep_ms(self.MIN_HOLD_TIME_MS)  # Hold ACK low long enough for slow client to see it
        if DEBUG:
            self._log_pin_states()
        return nibble

    def set_write_mode(self):
        self._set_data_pins_output()
        return
    
    def set_read_mode(self):
        self._set_data_pins_input()
        return

    def write(self, data):
        """Write data (compatible with UART interface)"""
        if isinstance(data, str):
            data = data.encode()

        for byte in data:
            self._write_byte(byte)

        return len(data)

    def read(self, size=1):
        """Read data (compatible with UART interface)"""
        result = bytearray()

        for _ in range(size):
            byte = self._read_byte()
            if byte is None:
                break
            result.append(byte)

        return bytes(result)

    def init(self, **kwargs):
        """Reconfigure interface (for compatibility with UART)"""
        # GPIO mode doesn't support reconfiguration like UART
        pass

    def cleanup(self):
        """Cleanup GPIO resources"""
        # No cleanup needed for MicroPython
        pass


class GPIO8Bit(GPIO):
    MODE = "8bit"
    DATA_WIDTH = 8

    def _write_byte(self, byte):
        """Write byte in 8-bit parallel mode"""
        self._set_data_pins_output()

        # Set data pins
        for i, pin in enumerate(self.data):
            pin.value((byte >> i) & 1)

        self.valid.value(1)
        self._wait_until_ack_is(1)
        self.valid.value(0)
        self._wait_until_ack_is(0)

    def _read_byte(self):
        """Read byte in 8-bit parallel mode"""
        self._set_data_pins_input()

        self._wait_until_valid_is(1)
        # Read data pins
        byte = 0
        for i, pin in enumerate(self.data):
            if pin.value():
                byte |= 1 << i
        self.ack.value(1)
        self._wait_until_valid_is(0)
        self.ack.value(0)

        return byte


class GPIO4Bit(GPIO):
    MODE = "4bit"
    DATA_WIDTH = 4

    def _write_byte(self, byte):
        """Write byte in 4-bit nibble mode (high nibble first)"""
        high_nibble = (byte >> 4) & 0x0F
        low_nibble = byte & 0x0F

        self._write_nibble(high_nibble)
        self._write_nibble(low_nibble)

    def _read_byte(self):
        """Read byte in 4-bit nibble mode (high nibble first)"""
        high_nibble = self._read_nibble()
        if high_nibble is None:
            return None
        low_nibble = self._read_nibble()
        if low_nibble is None:
            return None

        return (high_nibble << 4) | low_nibble
