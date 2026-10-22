"""shrink_preview.py: make the preview PNG small enough to attach to a card.

The preview is a flat dark image with a handful of colours, so a palette
quantised PNG is the same picture at a fraction of the bytes. The size and the
pixels are checked after the conversion, so a lossy palette cannot pass
unnoticed.

Usage:
    shrink_preview.py in.png out.png
"""

from __future__ import annotations

import os
import sys

from PIL import Image


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print(__doc__)
        return 2
    source, target = argv
    original = Image.open(source).convert("RGB")
    quantised = original.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE)
    quantised.save(target, optimize=True)

    # The palette version must keep the same size and stay close in colour.
    back = quantised.convert("RGB")
    original_array = original.tobytes()
    back_array = back.tobytes()
    differing = sum(1 for a, b in zip(original_array, back_array) if a != b)
    total = len(original_array)
    error = differing / float(total)

    print("  %dx%d, %d bytes -> %d bytes, %.4f of the bytes differ"
          % (original.width, original.height, os.path.getsize(source),
             os.path.getsize(target), error))
    if back.size != original.size:
        print("  FAIL the size changed")
        return 1
    if error > 0.01:
        print("  FAIL the palette version differs too much")
        return 1
    print("  PASS %s is %d bytes" % (os.path.basename(target), os.path.getsize(target)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
