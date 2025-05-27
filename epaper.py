from machine import SPI, Pin
from epaper1in54 import EPD_1in54
import time

# Pin config based on your wiring
SCK = 6
MOSI = 7
CS = 5
DC = 8
RST = 9
BUSY = 10

spi = SPI(0, baudrate=2000000, polarity=0, phase=0, sck=Pin(6), mosi=Pin(7))
epd = EPD_1in54(spi, cs=5, dc=8, rst=9, busy=10)

epd.clear()
epd.draw_text(10, 10, "Hello, world!", color=0)
#epd.draw_rect(5, 5, 120, 30, color=0)
#epd.draw_line(0, 0, 199, 199, color=0)
epd.show()

#time.sleep(3)
#epd.clear()
epd.sleep()
