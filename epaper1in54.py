from machine import Pin, SPI
import framebuf
import time


class EnhancedFrameBuffer(framebuf.FrameBuffer):
    def __init__(self, buffer, width, height, format):
        super().__init__(buffer, width, height, format)
        self.width = width
        self.height = height

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
        self.fb = EnhancedFrameBuffer(self.buffer, self.width, self.height, framebuf.MONO_HLSB)

        # Orientation settings
        self.flip_horizontal = False
        self.flip_vertical = False
        self.rotation = 0  # Can be 0, 90, 180, 270
        
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

    def set_rotation(self, angle):
        assert angle in (0, 90, 180, 270)
        self.rotation = angle

    def set_flip(self, horizontal=False, vertical=False):
        self.flip_horizontal = horizontal
        self.flip_vertical = vertical

    def show(self):
        transformed = bytearray(len(self.buffer))

        for y in range(self.height):
            for x in range(self.width):
                # Source bit
                src_index = x // 8 + y * (self.width // 8)
                src_bit = 7 - (x % 8)
                pixel = (self.buffer[src_index] >> src_bit) & 0x01

                # Apply flipping
                tx, ty = x, y
                if self.flip_horizontal:
                    tx = self.width - 1 - tx
                if self.flip_vertical:
                    ty = self.height - 1 - ty

                # Apply rotation
                if self.rotation == 90:
                    tx, ty = ty, self.width - 1 - tx
                elif self.rotation == 180:
                    tx, ty = self.width - 1 - tx, self.height - 1 - ty
                elif self.rotation == 270:
                    tx, ty = self.height - 1 - ty, tx

                # Target bit
                dst_index = tx // 8 + ty * (self.width // 8)
                dst_bit = 7 - (tx % 8)

                if pixel:
                    transformed[dst_index] |= (1 << dst_bit)
                else:
                    transformed[dst_index] &= ~(1 << dst_bit)

        self.send_cmd(0x24)
        self.send_data(transformed)

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

