"""
EPD_1in54 driver for Waveshare 1.54" V2 e-Paper Display (SSD1681)
Enhanced version with:
- Partial refresh support
- Busy timeout
- Display size configurability
- Image loading (PBM format)
- LUT management
- Dirty buffer optimization
- Sleep and wake control
- Inline documentation with datasheet links

Datasheet: https://www.waveshare.com/wiki/1.54inch_e-Paper_Module
"""

from machine import Pin, SPI
import framebuf
import time

BUSY_TIMEOUT_MS = 5000  # Timeout for busy-wait in milliseconds

class EPD_1in54:
    def __init__(self, spi, cs, dc, rst, busy, width=200, height=200):
        self.width = width
        self.height = height

        self.cs = Pin(cs, Pin.OUT)
        self.dc = Pin(dc, Pin.OUT)
        self.rst = Pin(rst, Pin.OUT)
        self.busy = Pin(busy, Pin.IN)
        self.spi = spi

        self.buffer = bytearray(self.width * self.height // 8)
        self.fb = framebuf.FrameBuffer(self.buffer, self.width, self.height, framebuf.MONO_HLSB)

        self.flip_horizontal = False
        self.flip_vertical = False
        self.rotation = 0
        self.dirty = False

        self.init()

    def reset(self):
        # Hardware reset sequence for the SSD1681 controller.
        # Pulling RST low then high ensures the controller resets correctly.
        # The 200ms delay is based on datasheet recommendations for stable reset.
        self.rst.value(0)
        time.sleep_ms(200)
        self.rst.value(1)
        time.sleep_ms(200)

    def send_cmd(self, cmd):
        # Sends a command byte to the display controller.
        # The D/C pin is set low for commands to distinguish them from data.
        # Refer to SSD1681 datasheet section 7.1 for interface control logic.
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytearray([cmd]))
        self.cs.value(1)

    def send_data(self, data):
        # Sends data byte(s) to the display controller.
        # The D/C pin is set high for data to differentiate it from commands.
        self.dc.value(1)
        self.cs.value(0)
        if isinstance(data, int):
            self.spi.write(bytearray([data]))
        else:
            self.spi.write(data)
        self.cs.value(1)

    def wait_busy(self, timeout_ms=BUSY_TIMEOUT_MS):
        start = time.ticks_ms()
        while self.busy.value() == 1:
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                raise RuntimeError("EPD busy timeout exceeded")
            time.sleep_ms(50)

    def init(self):
        self.reset()
        self.wait_busy()

        # SWRESET [datasheet 10.1.1]
        self.send_cmd(0x12)
        self.wait_busy()

        # Driver output control [datasheet 10.1.2]
        self.send_cmd(0x01)
        self.send_data(0xC7)  # 199
        self.send_data(0x00)
        self.send_data(0x00)

        # Data entry mode [datasheet 10.1.6]
        self.send_cmd(0x11)
        self.send_data(0x01)

        # Set RAM X-address [datasheet 10.1.7]
        self.send_cmd(0x44)
        self.send_data(0x00)
        self.send_data((self.width // 8) - 1)

        # Set RAM Y-address [datasheet 10.1.8]
        self.send_cmd(0x45)
        self.send_data(0xC7)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_cmd(0x3C)  # Border waveform
        self.send_data(0x01)

        self.send_cmd(0x18)
        self.send_data(0x80)

        self.send_cmd(0x22)  # Load LUT
        self.send_data(0xB1)
        self.send_cmd(0x20)
        self.wait_busy()

    def clear(self, color=0xFF):
        for i in range(len(self.buffer)):
            self.buffer[i] = color
        self.dirty = True
        self.show()

    def set_rotation(self, angle):
        assert angle in (0, 90, 180, 270)
        self.rotation = angle
        self.dirty = True

    def set_flip(self, horizontal=False, vertical=False):
        self.flip_horizontal = horizontal
        self.flip_vertical = vertical
        self.dirty = True

    def show(self, partial=False):
        if not self.dirty:
            return

        # Transformation logic for the framebuffer:
        # - This converts the logical framebuffer content based on flip and rotation settings.
        # - Pixel-by-pixel transformation is applied to a temporary buffer used for display.
        # - Horizontal flip inverts the x-axis; vertical flip inverts the y-axis.
        # - Rotation swaps and reindexes x and y coordinates to rotate by 90, 180, or 270 degrees.

        transformed = bytearray(len(self.buffer))
        for y in range(self.height):
            for x in range(self.width):
                src_index = x // 8 + y * (self.width // 8)
                src_bit = 7 - (x % 8)
                pixel = (self.buffer[src_index] >> src_bit) & 0x01

                tx, ty = x, y
                if self.flip_horizontal:
                    tx = self.width - 1 - tx
                if self.flip_vertical:
                    ty = self.height - 1 - ty

                if self.rotation == 90:
                    tx, ty = ty, self.width - 1 - tx
                elif self.rotation == 180:
                    tx, ty = self.width - 1 - tx, self.height - 1 - ty
                elif self.rotation == 270:
                    tx, ty = self.height - 1 - ty, tx

                dst_index = tx // 8 + ty * (self.width // 8)
                dst_bit = 7 - (tx % 8)

                if pixel:
                    transformed[dst_index] |= (1 << dst_bit)
                else:
                    transformed[dst_index] &= ~(1 << dst_bit)

        self.send_cmd(0x24)  # Write RAM
        self.send_data(transformed)

        self.send_cmd(0x22)
        self.send_data(0xF7 if not partial else 0xFF)  # 0xFF = partial refresh waveform
        self.send_cmd(0x20)
        self.wait_busy()

        self.dirty = False

    def sleep(self):
        self.send_cmd(0x10)
        self.send_data(0x01)

    def wake(self):
        self.init()
        self.dirty = True

    def load_pbm(self, filepath):
        with open(filepath, 'rb') as f:
            header = f.readline()
            if header.strip() != b'P4':
                raise ValueError("Unsupported PBM format")
            while True:
                line = f.readline()
                if not line.startswith(b'#'):
                    break
            w, h = [int(i) for i in line.strip().split()]
            if w != self.width or h != self.height:
                raise ValueError("Image size mismatch")
            self.buffer[:] = f.read(self.width * self.height // 8)
        self.dirty = True

    def load_lut(self, lut_data):
        self.send_cmd(0x32)
        self.send_data(lut_data)

    def draw_text(self, x, y, text, color=0):
        self.fb.text(text, x, y, color)
        self.dirty = True

    def draw_rect(self, x, y, w, h, color=0):
        self.fb.rect(x, y, w, h, color)
        self.dirty = True

    def draw_fill_rect(self, x, y, w, h, color=0):
        self.fb.fill_rect(x, y, w, h, color)
        self.dirty = True

    def draw_line(self, x1, y1, x2, y2, color=0):
        self.fb.line(x1, y1, x2, y2, color)
        self.dirty = True

    def draw_image(self, img_buf):
        if len(img_buf) != len(self.buffer):
            raise ValueError("Image buffer size mismatch")
        self.buffer[:] = img_buf
        self.dirty = True

