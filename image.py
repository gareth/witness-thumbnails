import logging
import os.path
import random
import sys
from typing import List, Optional, Tuple

# Pillow for Image processing.
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from PIL.PngImagePlugin import PngInfo

AP_COLORS = [
    (201, 118, 130),  # AP red
    (117, 194, 117),  # AP green
    (202, 148, 194),  # AP pink
    (217, 160, 125),  # AP orange
    (118, 126, 189),  # AP blue
    (238, 227, 145),  # AP yellow
]

if not os.path.isfile("fonts/Karmina Bold.otf"):
    logging.error(
        'Couldn\'t find font "Karmina Bold.otf". Please download this font and put it in the "fonts" subdirectory.'
    )
    exit(-1)


class Attributes:
    def __init__(self, seed: str, rows: int, cols: int) -> None:
        rand = random.Random(seed)
        self.background = AP_COLORS[rand.randrange(len(AP_COLORS))]
        self.fingerprint = [rand.choice([True, False]) for _ in range(rows * cols)]


def fontbox(text: str, size: int) -> Tuple[str, FreeTypeFont, Tuple[int, int, int, int]]:
    font = ImageFont.truetype("fonts/Karmina Bold.otf", size=size)
    box = font.getbbox(text)
    return text, font, box


class Thumbnail:
    def __init__(
        self,
        address: str,
        slot: str,
        seed: Optional[str] = None,
        rows: int = 24,
        cols: int = 3,
        width: int = 320,
        height: int = 180,
        old: bool = False,
    ) -> None:
        self.address = address
        self.slot = slot
        self.seed = seed
        self.width = width
        self.height = height
        self.rows = rows
        self.cols = cols
        self.old = old

        attributes = Attributes(seed or f"{address}|{slot}", self.rows, self.cols)

        if old:
            self.background = (110, 110, 110)
        else:
            self.background = attributes.background
        self.fingerprint = attributes.fingerprint

    def image(self) -> Image:
        try:
            (server_text, port_text) = self.address.rsplit(":", 2)
        except ValueError:
            (server_text, port_text) = (self.address, "38281")
        slot_text = self.slot

        ink = (30, 30, 60)  # Dark grey, nearly black, slightly blue

        image = Image.new("RGBA", (self.width, self.height), self.background)
        draw = ImageDraw.Draw(image)
        draw.fontmode = "l"  # Antialiased

        rows = self.layout([server_text, f":{port_text}", slot_text], [25, 80, 25], 5)

        layout_height = rows[-1][-1]

        padding_top = (self.height - layout_height) // 2
        padding_left = 40

        for text, font, (x, y), bottom in rows:
            draw.text((x + padding_left, y + padding_top), text, fill=ink, font=font)

        if self.old:
            text, font, bbox = fontbox("(old)", 25)
            _, _, width, height = bbox
            draw.text((self.width - width - 5, self.height - height - 5), text, fill=ink, font=font)

        for i, present in enumerate(self.fingerprint):
            cols = self.cols
            w = self.height / self.rows
            x, y = round(w * (i % cols)), round(w * (i // cols))
            if present:
                draw.rectangle((x, y, x + w, y + w), fill=(30, 30, 60))

        return image

    # Calculates the positions for successive lines of text at given font sizes so
    # they line up nicely on top of each other
    def layout(
        self, texts: List[str], sizes: List[int], spacing: int = 0
    ) -> List[Tuple[str, FreeTypeFont, Tuple[int, int], int]]:
        fontboxes = [fontbox(t, s) for (t, s) in zip(texts, sizes)]
        offset = 0

        outputs = []
        for text, font, bbox in fontboxes:
            (_, top, _, bottom) = bbox
            outputs.append((text, font, (0, offset - top), (offset - top + bottom)))
            offset += (bottom - top) + spacing

        return outputs


def make_thumbnail(address: str, slot: str, output_path: str, old: bool = False) -> None:
    thumb = Thumbnail(address, slot, old=old)

    metadata = PngInfo()
    metadata.add_text("WitnessThumbnailsTool", "WitnessThumbnailsTool")

    thumb.image().save(output_path, pnginfo=metadata)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        address, slot = sys.argv[1:3]
    else:
        port = random.randrange(10000, 65535)
        address, slot = (f"archipelago.gg:{port}", "Player")

    make_thumbnail(address, slot, f"output/{address}-{slot}.png")
