import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
import time
from adafruit_mcp3xxx.analog_in import AnalogIn
from pythonosc.udp_client import SimpleUDPClient

ip = "127.0.0.1"
port = 5009

try:
    client = SimpleUDPClient(ip, port)
except Exception as e:
    print(f"Failed to create OSC client: {e}")
    exit(1)

spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# chip select
cs_pins = [digitalio.DigitalInOut(pin) for pin in [board.D5, board.D6, board.D13, board.D19]]
mcps = [MCP.MCP3008(spi, cs) for cs in cs_pins]

# input chans for first MCP3008 chip (pots)
pot_channels = [AnalogIn(mcps[0], pin) for pin in [MCP.P0, MCP.P1, MCP.P2, MCP.P3, MCP.P4, MCP.P5]]

# input chans for togs and buttons
toggle_channels = []
pushbutton_channels = []

# second MCP3008 for toggles
for pin in [MCP.P0, MCP.P1, MCP.P2, MCP.P3, MCP.P4, MCP.P5, MCP.P6, MCP.P7]:
    toggle_channels.append(AnalogIn(mcps[1], pin))

# third MCP3008 for toggles
for pin in [MCP.P0, MCP.P1, MCP.P2, MCP.P3, MCP.P4, MCP.P5, MCP.P6, MCP.P7]:
    toggle_channels.append(AnalogIn(mcps[2], pin))

# fourth MCP3008 for toggles and buttons
for pin in [MCP.P0, MCP.P1, MCP.P2, MCP.P3]:
    toggle_channels.append(AnalogIn(mcps[3], pin))
for pin in [MCP.P4, MCP.P5, MCP.P6, MCP.P7]:
    pushbutton_channels.append(AnalogIn(mcps[3], pin))

previous_toggle_states = [None] * len(toggle_channels)
previous_button_states = [None] * len(pushbutton_channels)
last_change_time_toggles = [0] * len(toggle_channels)
last_change_time_buttons = [0] * len(pushbutton_channels)

DIGITAL_THRESHOLD = 32768
DEBOUNCE_TIME = 0.05

def read_digital_state(channel):
    """Read digital state from analog channel with proper threshold"""
    return 1 if channel.value > DIGITAL_THRESHOLD else 0

print("Starting MCP3008 OSC controller...")
print("Layout:")
print("  Chip 1 (D5):  6 potentiometers (P0-P5)")
print("  Chip 2 (D6):  8 toggle switches (P0-P7)")
print("  Chip 3 (D13): 8 toggle switches (P0-P7)")
print("  Chip 4 (D19): 4 toggle switches (P0-P3) + 4 push-buttons (P4-P7)")

while True:
    try:
        current_time = time.monotonic()
        
        # read and send pot values
        for i, chan in enumerate(pot_channels):
            print(f'Raw ADC Value Pot {i}: {chan.value}')
            print(f'ADC Voltage Pot {i}: {chan.voltage:.3f}V')
            client.send_message(f"/POT{i}", chan.value)

        # read and send tog values with debouncing
        for i, chan in enumerate(toggle_channels):
            current_state = read_digital_state(chan)
            
            if (current_state != previous_toggle_states[i] and 
                current_time - last_change_time_toggles[i] > DEBOUNCE_TIME):
                
                previous_toggle_states[i] = current_state
                last_change_time_toggles[i] = current_time
                
                print(f'Toggle {i}: {"ON" if current_state else "OFF"}')
                client.send_message(f"/TOGGLE{i}", current_state)

        # read and send button values with debouncing
        for i, chan in enumerate(pushbutton_channels):
            current_state = read_digital_state(chan)
            
            if (current_state != previous_button_states[i] and 
                current_time - last_change_time_buttons[i] > DEBOUNCE_TIME):
                
                previous_button_states[i] = current_state
                last_change_time_buttons[i] = current_time
                
                print(f'Pushbutton {i}: {"PRESSED" if current_state else "RELEASED"}')
                client.send_message(f"/BUTTON{i}", current_state)

        time.sleep(0.01)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        break
    except Exception as e:
        print(f"Error in main loop: {e}")
        time.sleep(0.01)  # Wait before retrying
        continue

print("Controller stopped.")