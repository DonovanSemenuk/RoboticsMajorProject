"""Generate print-ready ArUco marker images for the tour guide demo.

Produces:
  - marker_0.png ... marker_3.png  -- single markers with white quiet zone
                                       and ID label, ready to print one per page
  - markers_print_sheet.pdf        -- all four markers laid out for batch printing

Settings match src/tour_guide/config/aruco_params_real.yaml:
  dictionary  = DICT_4X4_50
  marker_size = 0.10 m  (the printed black square should measure exactly 10 cm)
"""

import os

import cv2
import numpy as np

DICTIONARY = cv2.aruco.DICT_4X4_50
IDS = [0, 1, 2, 3]

# Print at 300 DPI: 100 mm = 1181 px (round to 1200 for clean math).
MARKER_PX = 1200
QUIET_ZONE_PX = 240   # white border on each side, ~20 mm at 300 DPI
LABEL_PX = 120        # reserved space at the bottom for the ID caption

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def make_marker(marker_id: int) -> np.ndarray:
    aruco_dict = cv2.aruco.getPredefinedDictionary(DICTIONARY)
    marker = cv2.aruco.generateImageMarker(aruco_dict, marker_id, MARKER_PX)

    canvas_w = MARKER_PX + 2 * QUIET_ZONE_PX
    canvas_h = MARKER_PX + 2 * QUIET_ZONE_PX + LABEL_PX
    canvas = np.full((canvas_h, canvas_w), 255, dtype=np.uint8)

    y0 = QUIET_ZONE_PX
    x0 = QUIET_ZONE_PX
    canvas[y0:y0 + MARKER_PX, x0:x0 + MARKER_PX] = marker

    label = f"ID {marker_id}  |  DICT_4X4_50  |  100 mm"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.6
    thickness = 3
    (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, thickness)
    text_x = (canvas_w - text_w) // 2
    text_y = canvas_h - (LABEL_PX - text_h) // 2
    cv2.putText(canvas, label, (text_x, text_y), font, font_scale, 0, thickness, cv2.LINE_AA)

    return canvas


def main() -> None:
    pngs = []
    for mid in IDS:
        img = make_marker(mid)
        path = os.path.join(OUT_DIR, f"marker_{mid}.png")
        cv2.imwrite(path, img)
        pngs.append(path)
        print(f"wrote {path}  ({img.shape[1]}x{img.shape[0]} px)")

    try:
        from matplotlib import pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError:
        print("(matplotlib not installed -- skipping PDF sheet)")
        return

    pdf_path = os.path.join(OUT_DIR, "markers_print_sheet.pdf")
    with PdfPages(pdf_path) as pdf:
        for mid, png_path in zip(IDS, pngs):
            img = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.imshow(img, cmap="gray", vmin=0, vmax=255)
            ax.set_axis_off()
            ax.set_title(f"Marker ID {mid}  --  print at 100% scale", fontsize=14)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
