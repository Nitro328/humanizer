# -*- coding: utf-8 -*-
"""Image processing core for Android.

Applies a deterministic LUT of transformations (resampling, unsharp masking,
chromatic aberration, noise, blur, JPEG re-compression) to an image in order
to alter its AI-generation signature.

Exposes:
- process_image(input_path, output_path) -> str : core called by the Android app
- sweep(...) / build_sweep(...)                 : parameter search tooling

The 'apple' preset is the verified base recipe (83% APPLE, 100% WOMAN).
"""
import os

import cv2
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------
# Values of the consolidated peak on APPLE (83% ZeroGPT). Do NOT modify.
# Chromatic aberration values are expressed in pixels on a reference short
# side of 768 px and are rescaled according to the actual resolution.
APPLE_PRESET = {
    "resize_w": 1.0035,
    "resize_h": 1.0022,
    "sharp_w": 1.14,
    "sharp_b": -0.14,
    "sharp_sigma": 1.0,
    "ca_dx": 0.92,
    "ca_dy": 0.42,
    "noise_y": 1.35,
    "noise_c": 2.45,
    "blur_sigma": 0.34,
    "jpeg_quality": 86,
    "subsampling": 1,          # 4:2:2
    "downscale": 1.0,          # no downscale in the APPLE preset
    "seed": 42,
}

# Starting point for portraits. NOT verified on ZeroGPT: use the sweep.
WOMAN_PRESET = {
    "resize_w": 1.0035,
    "resize_h": 1.0022,
    "sharp_w": 1.14,
    "sharp_b": -0.14,
    "sharp_sigma": 1.0,
    "ca_dx": 0.92,
    "ca_dy": 0.42,
    "noise_y": 1.6,
    "noise_c": 2.8,
    "blur_sigma": 0.5,
    "jpeg_quality": 86,
    "subsampling": 1,
    "downscale": 0.8,
    "seed": 42,
}

PRESETS = {"apple": APPLE_PRESET, "woman": WOMAN_PRESET}

# Reference short side for chromatic aberration normalization.
_REF_MIN_DIM = 768.0


# ---------------------------------------------------------------------------
# Deterministic core
# ---------------------------------------------------------------------------
def apply_tuning(img_bgr, p):
    """Apply the tuning to a BGR frame (uint8) and return the BGR frame."""
    h, w = img_bgr.shape[:2]
    min_dim = min(h, w)
    scale = min_dim / _REF_MIN_DIM

    # 1. Optional downscale (destroys high-frequency artifacts)
    if p["downscale"] != 1.0:
        ws = int(round(w * p["downscale"]))
        hs = int(round(h * p["downscale"]))
        img_bgr = cv2.resize(img_bgr, (ws, hs), interpolation=cv2.INTER_AREA)

    # 2. Peak geometric resampling (Cubic + Area)
    # NOTE: int() truncates toward zero (as in the original code), it does NOT round.
    w_mid = int(w * p["resize_w"])
    h_mid = int(h * p["resize_h"])
    intermediate = cv2.resize(img_bgr, (w_mid, h_mid), interpolation=cv2.INTER_CUBIC)
    resized = cv2.resize(intermediate, (w, h), interpolation=cv2.INTER_AREA)

    # 3. Unsharp masking
    gaussian_sharp = cv2.GaussianBlur(resized, (0, 0), p["sharp_sigma"])
    unsharp = cv2.addWeighted(resized, p["sharp_w"], gaussian_sharp, p["sharp_b"], 0)

    # 4. Chromatic aberration normalized to the resolution
    dx = p["ca_dx"] * scale
    dy = p["ca_dy"] * scale
    b, g, r = cv2.split(unsharp)
    m_r = np.float32([[1, 0, dx], [0, 1, dy]])
    m_b = np.float32([[1, 0, -dx], [0, 1, -dy]])
    r_shift = cv2.warpAffine(r, m_r, (w, h), borderMode=cv2.BORDER_REFLECT)
    b_shift = cv2.warpAffine(b, m_b, (w, h), borderMode=cv2.BORDER_REFLECT)
    img_chroma = cv2.merge([b_shift, g, r_shift])

    # 5. Deterministic YCrCb noise (same RNG stream as the original preset)
    np.random.seed(p["seed"])
    noise_y = np.random.normal(0, p["noise_y"], (h, w)).astype(np.float32)
    noise_cr = np.random.normal(0, p["noise_c"], (h, w)).astype(np.float32)
    noise_cb = np.random.normal(0, p["noise_c"], (h, w)).astype(np.float32)

    ycrcb = cv2.cvtColor(img_chroma, cv2.COLOR_BGR2YCrCb).astype(np.float32)
    ycrcb[:, :, 0] = np.clip(ycrcb[:, :, 0] + noise_y, 0, 255)
    ycrcb[:, :, 1] = np.clip(ycrcb[:, :, 1] + noise_cr, 0, 255)
    ycrcb[:, :, 2] = np.clip(ycrcb[:, :, 2] + noise_cb, 0, 255)
    img_noisy = cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2BGR)

    # 6. Transition blur
    filtered = cv2.GaussianBlur(img_noisy, (3, 3), p["blur_sigma"])

    return filtered


def save_jpeg(img_bgr, output_path, p):
    pil_img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    pil_img.save(output_path, "JPEG", quality=p["jpeg_quality"],
                 subsampling=p["subsampling"], optimize=True)


def process(input_path, output_path, preset="apple"):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Cannot find {input_path}")
    p = PRESETS[preset]
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Cannot read image {input_path}")
    result = apply_tuning(img, p)
    save_jpeg(result, output_path, p)
    print(f"[OK] preset={preset} -> {output_path}")


def absolute_peak_tuning(input_path, output_path):
    """Keep the historical behavior (apple preset)."""
    process(input_path, output_path, preset="apple")


def process_image(input_path: str, output_path: str | None = None) -> str:
    """Core for Android: process a .jpg and return the result path.

    No terminal or UI dependency: it receives the full file path, applies the
    deterministic tuning and returns where the result was saved. By default the
    output keeps the same name with the '_humanized' suffix, all lowercase
    (e.g. 'pippo.jpg' -> 'pippo_humanized.jpg').
    """
    if output_path is None:
        stem = os.path.splitext(os.path.basename(input_path))[0].lower()
        out_dir = os.path.dirname(input_path) or "."
        output_path = os.path.join(out_dir, f"{stem}_humanized.jpg")
    # The 'apple' preset is the verified base recipe (83% APPLE, 100% WOMAN).
    process(input_path, output_path, preset="apple")
    return output_path


# ---------------------------------------------------------------------------
# Deterministic sweep (LUT of candidates to test on ZeroGPT)
# ---------------------------------------------------------------------------
def build_sweep():
    base = dict(APPLE_PRESET)
    sweeps = []

    def add(tag, **kw):
        p = dict(base)
        p.update(kw)
        sweeps.append((tag, p))

    add("base")
    for v in (1.0, 1.8, 2.4, 3.2):
        add(f"ny{v:g}", noise_y=v)
    for v in (1.8, 3.0, 4.0):
        add(f"nc{v:g}", noise_c=v)
    for v in (0.2, 0.5, 0.9, 1.4):
        add(f"blur{v:g}", blur_sigma=v)
    for v in (1.05, 1.25, 1.5):
        add(f"sharp{v:g}", sharp_w=v)
    for v in (78, 90):
        add(f"q{v}", jpeg_quality=v)
    for v in (0.9, 0.75, 0.6):
        add(f"down{v:g}", downscale=v)
    # Aggressive combinations to break the DALL-E signature
    add("agg1", downscale=0.7, noise_y=2.0, blur_sigma=0.6, jpeg_quality=82)
    add("agg2", downscale=0.6, noise_y=2.5, noise_c=3.0, blur_sigma=0.8,
        jpeg_quality=80)
    add("agg3", downscale=0.75, sharp_w=1.35, noise_c=3.0, blur_sigma=0.5)
    return sweeps


def sweep(input_path, out_dir):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Cannot find {input_path}")
    os.makedirs(out_dir, exist_ok=True)
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Cannot read image {input_path}")

    sweeps = build_sweep()
    print(f"{'file':<16} {'noise_y':>8} {'noise_c':>8} {'blur':>6} "
          f"{'sharp':>6} {'down':>6} {'q':>4}")
    for tag, p in sweeps:
        result = apply_tuning(img, p)
        out = os.path.join(out_dir, f"{tag}.jpg")
        save_jpeg(result, out, p)
        print(f"{tag + '.jpg':<16} {p['noise_y']:>8} {p['noise_c']:>8} "
              f"{p['blur_sigma']:>6} {p['sharp_w']:>6} "
              f"{p['downscale']:>6} {p['jpeg_quality']:>4}")
    print(f"\n[OK] {len(sweeps)} candidates saved to {out_dir}")


# ---------------------------------------------------------------------------
# Entry point (terminal, local testing only)
# ---------------------------------------------------------------------------
def main():
    """Terminal entry point: ask for the full .jpg filename."""
    name = input("Enter the full .jpg filename: ").strip().strip('"').strip("'")
    if not name:
        print("Error: no file specified.")
        return
    try:
        out = process_image(name)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return
    print(f"[OK] Result saved to: {out}")


if __name__ == "__main__":
    main()
