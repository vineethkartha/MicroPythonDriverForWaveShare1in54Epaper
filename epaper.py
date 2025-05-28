from machine import SPI, Pin
from epaper1in54 import EPD_1in54
import time

# --- Pin Configuration ---
SCK = 6
MOSI = 7
CS = 5
DC = 8
RST = 9
BUSY = 10

# --- Initialize SPI ---
spi = SPI(0, baudrate=2000000, polarity=0, phase=0,
          sck=Pin(SCK), mosi=Pin(MOSI))

# --- Initialize e-Paper display ---
epd = EPD_1in54(spi, cs=CS, dc=DC, rst=RST, busy=BUSY)

# --- Setup ---
epd.set_flip(horizontal=True)
epd.set_rotation(0)

# --- Initial Draw and Full Refresh ---
epd.clear()
epd.draw_text(10, 10, "Hello, world!", color=0)
epd.show(partial=False)  # Full refresh
time.sleep(3)

# --- Partial Update ---
epd.draw_text(10, 30, "Partial update!", color=0)
epd.show(partial=True)  # Only update the changed region

# --- Final Sleep ---
time.sleep(5)
epd.sleep()

