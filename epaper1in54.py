from machine import Pin, SPI
import framebuf
import time

class EPD_1in54:
    def __init__(self, spi, cs, dc, rst, busy):
        self.width = 200
        self.height = 200

        self.cs = Pin(cs, Pin.OUT)
        self.dc = Pin(dc, Pin.OUT)
        self.rst = Pin(rst, Pin.OUT)
        self.busy = Pin(busy, Pin.IN)
        self.spi = spi

        self.buffer = bytearray(self.width * self.height // 8)
        self.fb = framebuf.FrameBuffer(self.buffer, self.width, self.height, framebuf.MONO_HLSB)

        self.init()

    def reset(self):
        self.rst.value(0)
        time.sleep_ms(200)
        self.rst.value(1)
        time.sleep_ms(200)

    def send_cmd(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytearray([cmd]))
        self.cs.value(1)

    def send_data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(bytearray([data]) if isinstance(data, int) else data)
        self.cs.value(1)

    def wait_busy(self):
        while self.busy.value() == 1:
            time.sleep_ms(50)

    def init(self):
        self.reset()
        self.wait_busy()
        self.send_cmd(0x12)  # SWRESET
        self.wait_busy()

        self.send_cmd(0x01)  # Driver output control
        self.send_data(0xC7)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_cmd(0x11)  # Data entry mode
        self.send_data(0x01)

        self.send_cmd(0x44)  # RAM X address
        self.send_data(0x00)
        self.send_data(0x18)  # 200/8 - 1

        self.send_cmd(0x45)  # RAM Y address
        self.send_data(0xC7)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_cmd(0x3C)  # Border Waveform
        self.send_data(0x01)

        self.send_cmd(0x18)
        self.send_data(0x80)

        self.send_cmd(0x22)
        self.send_data(0xB1)
        self.send_cmd(0x20)
        self.wait_busy()

    def clear(self, color=0xFF):
        for i in range(len(self.buffer)):
            self.buffer[i] = color
        self.show()

    def show(self):
        self.send_cmd(0x24)
        self.send_data(self.buffer)

        self.send_cmd(0x22)
        self.send_data(0xF7)
        self.send_cmd(0x20)
        self.wait_busy()

    def sleep(self):
        self.send_cmd(0x10)
        self.send_data(0x01)

    # Drawing helpers
    def draw_text(self, x, y, text, color=0):
        self.fb.text(text, x, y, color)

    def draw_rect(self, x, y, w, h, color=0):
        self.fb.rect(x, y, w, h, color)

    def draw_fill_rect(self, x, y, w, h, color=0):
        self.fb.fill_rect(x, y, w, h, color)

    def draw_line(self, x1, y1, x2, y2, color=0):
        self.fb.line(x1, y1, x2, y2, color)

    def draw_image(self, img_buf):
        # img_buf must be same size: 200x200 / 8 bytes
        self.buffer[:] = img_buf
