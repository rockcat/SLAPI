import sys

from transport import Transport
from gpio_transport import GPIO4Bit, GPIO8Bit
from serial_transport import Serial
from env import read_env


def load_config() -> Transport:

    # Load configuration from env.txt
    env = read_env()

    # Determine interface type from env
    mode = env.get('MODE', 'uart')

    if mode == 'uart':
        port = int(env.get('PORT', 0))
        baud = int(env.get('BAUD', 9600))
        bits = int(env.get('BITS', 8))
        txPin = int(env.get('TX_PIN', 0))
        rxPin = int(env.get('RX_PIN', 1))
        rts = int(env.get('RTS_PIN', 0))
        rts = None if rts == 0 else rts
        cts = int(env.get('CTS_PIN', 0))
        cts = None if cts == 0 else cts
        parity_str = env.get('PARITY', 'None')
        parity = None if parity_str == 'None' else (0 if parity_str == 'E' else 1)
        stop = int(env.get('STOP', 1))

        rxbuf = int(env.get('RXBUF', 512))
        txbuf = int(env.get('TXBUF', 512))

        print(f"Using UART: port={port}, baud={baud}, bits={bits}, parity={parity_str}, stop={stop} ", file=sys.stderr)
        print(f"GPIO: tx={txPin}, rx={rxPin}, rts={rts}, cts={cts}", file=sys.stderr)

        serial = Serial(
            port,
            baudrate=baud,
            bits=bits,
            parity=parity,
            stop=stop,
            tx=txPin,
            rx=rxPin,
            rts=rts,
            cts=cts,
            rxbuf=rxbuf,
            txbuf=txbuf,
        )
        print(f"flow={serial.flow}, rxbuf={rxbuf}, txbuf={txbuf}", file=sys.stderr)
        return serial
        
    elif mode == 'gpio-8bit':
        data_pins = [int(p.strip()) for p in env.get('DATA_PINS', '').split(',')]
        valid_pin = int(env.get('VALID_PIN', 0))
        ack_pin = int(env.get('ACK_PIN', 0))
        timeout_ms = int(env.get('TIMEOUT_MS', 0))
        min_hold_time_ms = int(env.get('MIN_HOLD_TIME_MS', 10)) # Default to 10ms if not specified
        
        if len(data_pins) != 8:
            print("Error: gpio-8bit mode requires 8 DATA_PINS", file=sys.stderr)
            sys.exit(1)
        
        print(f"Using 8-bit GPIO: data={data_pins}, valid={valid_pin}, ack={ack_pin}", file=sys.stderr)
        gpio = GPIO8Bit(data_pins, valid_pin, ack_pin, timeout_ms, min_hold_time_ms)
        return gpio
        
    elif mode == 'gpio-4bit':
        data_pins = [int(p.strip()) for p in env.get('DATA_PINS', '').split(',')]
        valid_pin = int(env.get('VALID_PIN', 0))
        ack_pin = int(env.get('ACK_PIN', 0))
        timeout_ms = int(env.get('TIMEOUT_MS', 0))
        min_hold_time_ms = int(env.get('MIN_HOLD_TIME_MS', 10)) # Default to 10ms if not specified
        if len(data_pins) != 4:
            print("Error: gpio-4bit mode requires 4 DATA_PINS", file=sys.stderr)
            sys.exit(1)
        
        print(f"Using 4-bit GPIO: data={data_pins}, valid={valid_pin}, ack={ack_pin}", file=sys.stderr)
        gpio = GPIO4Bit(data_pins, valid_pin, ack_pin, timeout_ms, min_hold_time_ms)
        return gpio
    
    else:
        print(f"Error: Unknown MODE '{mode}' in env.txt", file=sys.stderr)
        sys.exit(1)
        
