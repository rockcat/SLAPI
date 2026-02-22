# MicroPython imports
from transport import Transport
from machine import UART

class Serial(Transport):
    """UART-based transport implementation."""

    def __init__(
        self,
        port,
        baudrate=9600,
        bits=8,
        parity=None,
        stop=1,
        tx=None,
        rx=None,
        rts=None,
        cts=None,
        flow=None,
        rxbuf=512,
        txbuf=512,
    ):
        self.port = port
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.tx = tx
        self.rx = rx
        self.rts = rts
        self.cts = cts

        if flow is None:
            flow = 0
            if rts is not None:
                flow |= UART.RTS
            if cts is not None:
                flow |= UART.CTS

        self.flow = flow
        self.uart = UART(
            port,
            baudrate=baudrate,
            bits=bits,
            parity=parity,
            stop=stop,
            tx=tx,
            rx=rx,
            rts=rts,
            cts=cts,
            flow=flow,
            rxbuf=rxbuf,
            txbuf=txbuf,
        )

    def set_write_mode(self):
        # UART is full-duplex, so no mode switching needed
        pass

    def set_read_mode(self):
        # UART is full-duplex, so no mode switching needed
        pass

    def write(self, data):
        return self.uart.write(data)

    def read(self, size=1):
        return self.uart.read(size)

    def init(self, **kwargs):
        return self.uart.init(**kwargs)

    def cleanup(self):
        pass

    def __repr__(self):
        return f"Serial(port={self.port}, baudrate={self.baudrate})"
