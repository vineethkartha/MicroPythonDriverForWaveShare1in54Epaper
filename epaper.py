from machine import SPI, Pin
from epaper1in54 import EPD_1in54
from writer import Writer
import freesans20  # Make sure this .py font file is on your Pico
import time

# Pin config
SCK = 6
MOSI = 7
CS = 5
DC = 8
RST = 9
BUSY = 10

# SPI and Display Setup
spi = SPI(0, baudrate=2000000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI))
epd = EPD_1in54(spi, cs=CS, dc=DC, rst=RST, busy=BUSY)

# Optional: Fix mirroring or rotation
epd.set_flip(horizontal=True)
epd.set_rotation(0)  # Or 90, 180, 270

# Clear and draw text with larger font
epd.clear()

# Create Writer instance with the enhanced framebuffer
wri = Writer(epd.fb, freesans20)
wri.set_textpos(10, 10)  # (row, column)
wri.printstring("Hello, world!")

epd.show()
epd.sleep()

