import os
import re
import math
import aiofiles
import aiohttp
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from youtubesearchpython.__future__ import VideosSearch

from AnonXMusic import app
from config import YOUTUBE_IMG_URL


# ── HELPERS ───────────────────────────────────────────────────────────────────

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight), Image.LANCZOS)


def circle(img):
    img = img.convert("RGBA")
    h, w = img.size
    mask = Image.new("L", (h, w), 0)
    ImageDraw.Draw(mask).ellipse([(0, 0), (h, w)], fill=255)
    result = Image.new("RGBA", (h, w), (0, 0, 0, 0))
    result.paste(img, mask=mask)
    return result


def clear(text, limit=40):
    words = text.split(" ")
    title = ""
    for w in words:
        if len(title) + len(w) + 1 <= limit:
            title += (" " if title else "") + w
        else:
            break
    return title.strip() or text[:limit]


def get_dominant_color(img: Image.Image, n=4):
    """Return most vibrant dominant colour via fast downsampled clustering."""
    small = img.convert("RGB").resize((60, 60))
    arr = np.array(small).reshape(-1, 3).astype(float)
    
    # Fast sampling
    idx = np.random.choice(len(arr), min(n, len(arr)), replace=False)
    centers = arr[idx]
    
    for _ in range(6):  # reduced iterations for fast processing
        dists = np.linalg.norm(arr[:, None] - centers[None], axis=2)
        labels = np.argmin(dists, axis=1)
        for k in range(n):
            pts = arr[labels == k]
            if len(pts) > 0:
                centers[k] = pts.mean(axis=0)
                
    best, best_sat = centers[0], -1.0
    for c in centers:
        r, g, b = c / 255.0
        mx, mn = max(r, g, b), min(r, g, b)
        sat = (mx - mn) / (mx + 1e-9)
        lum = (mx + mn) / 2
        score = sat * (1 - abs(lum - 0.5))
        if score > best_sat:
            best_sat, best = score, c
            
    return tuple(int(x) for x in best)


def build_palette(base):
    RAINBOW = [
        (0x1E, 0x90, 0xFF),  # Blue
        (0x06, 0xB6, 0xD4),  # Cyan
        (0x14, 0xB8, 0xA6),  # Teal
        (0x22, 0xC5, 0x5E),  # Green
        (0xF5, 0x9E, 0x0B),  # Amber
        (0xF9, 0x73, 0x16),  # Orange
        (0xF4, 0x3F, 0x5E),  # Rose
        (0xEC, 0x48, 0x99),  # Pink
        (0xA8, 0x55, 0xF7),  # Purple
        (0xE2, 0xE8, 0xF0),  # White
    ]
    br, bg, bb = base

    def dist(c):
        return math.sqrt((c[0] - br) ** 2 * 0.299 + (c[1] - bg) ** 2 * 0.587 + (c[2] - bb) ** 2 * 0.114)

    best_idx = min(range(len(RAINBOW)), key=lambda i: dist(RAINBOW[i]))
    return RAINBOW[best_idx:] + RAINBOW[:best_idx]


def make_neon_glow_border(size, bbox, dominant, radius=30, stroke=6, glow_layers=10):
    NEON = [
        (0x1E, 0x90, 0xFF), (0x06, 0xB6, 0xD4), (0x14, 0xB8, 0xA6),
        (0x22, 0xC5, 0x5E), (0xF5, 0x9E, 0x0B), (0xF9, 0x73, 0x16),
        (0xF4, 0x3F, 0x5E), (0xEC, 0x48, 0x99), (0xA8, 0x55, 0xF7), (0xE2, 0xE8, 0xF0)
    ]
    br, bg, bb = dominant

    def dist(c):
        return math.sqrt((c[0] - br) ** 2 * 0.299 + (c[1] - bg) ** 2 * 0.587 + (c[2] - bb) ** 2 * 0.114)

    sorted_neon = sorted(NEON, key=dist)
    nr, ng, nb = sorted_neon[0]
    nr2, ng2, nb2 = sorted_neon[1]

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    x0, y0, x1, y1 = bbox
    ld = ImageDraw.Draw(layer)

    # Outer soft glow halo
    for i in range(glow_layers, 0, -1):
        t = i / glow_layers
        expand = int(t ** 0.5 * glow_layers * 4)
        alpha = int(4 + (1 - t) ** 1.2 * 140)
        w = stroke + int(t * glow_layers * 2)
        lx0 = max(0, x0 - expand)
        ly0 = max(0, y0 - expand)
        lx1 = min(size[0], x1 + expand)
        ly1 = min(size[1], y1 + expand)
        cr, cg, cb = (nr, ng, nb) if i % 2 == 0 else (nr2, ng2, nb2)
        ld.rounded_rectangle(
            (lx0, ly0, lx1, ly1),
            radius=max(6, radius - expand // 6),
            outline=(cr, cg, cb, alpha),
            width=w
        )

    # Bright inner glow
    for s in range(4, 0, -1):
        alpha = 60 + s * 35
        ld.rounded_rectangle(
            (x0 - s, y0 - s, x1 + s, y1 + s),
            radius=radius,
            outline=(min(255, nr + 60), min(255, ng + 60), min(255, nb + 60), alpha),
            width=stroke + s
        )

    # Primary stroke
    ld.rounded_rectangle(
        bbox, radius=radius,
        outline=(min(255, nr + 90), min(255, ng + 90), min(255, nb + 90), 255),
        width=stroke
    )

    # White centre highlight
    ld.rounded_rectangle(
        bbox, radius=radius,
        outline=(255, 255, 255, 90),
        width=max(1, stroke // 3)
    )

    return layer


def draw_glowing_progress_bar(draw, canvas, x0, y0, x1, bar_h, thumb_frac, palette):
    draw.rounded_rectangle(
        [(x0, y0), (x1, y0 + bar_h)],
        radius=bar_h // 2,
        fill=(50, 50, 80, 160)
    )

    thumb_x = int(x0 + (x1 - x0) * thumb_frac)
    base_col = palette[0]
    accent = palette[3]

    for glow in range(6, 0, -1):
        gr, gg, gb = base_col
        ga = int(15 + (6 - glow) * 18)
        gpad = glow * 2
        draw.rounded_rectangle(
            [(x0, y0 - gpad // 2), (thumb_x, y0 + bar_h + gpad // 2)],
            radius=bar_h // 2 + gpad // 2,
            fill=(min(255, gr + 60), min(255, gg + 60), min(255, gb + 60), ga)
        )

    r1, g1, b1 = base_col
    r2, g2, b2 = accent
    draw.rounded_rectangle(
        [(x0, y0), (thumb_x, y0 + bar_h)],
        radius=bar_h // 2,
        fill=(min(255, r1 + 80), min(255, g1 + 80), min(255, b1 + 80), 240)
    )
    draw.rounded_rectangle(
        [(x0, y0), (thumb_x, y0 + bar_h // 3)],
        radius=bar_h // 2,
        fill=(min(255, r2 + 100), min(255, g2 + 100), min(255, b2 + 100), 120)
    )

    TR = 10
    cy = y0 + bar_h // 2
    for glow in range(5, 0, -1):
        gr, gg, gb = accent
        ga = int(20 + (5 - glow) * 25)
        gr_r = TR + glow * 3
        draw.ellipse(
            [(thumb_x - gr_r, cy - gr_r), (thumb_x + gr_r, cy + gr_r)],
            fill=(min(255, gr + 80), min(255, gg + 80), min(255, gb + 80), ga)
        )
    draw.ellipse(
        [(thumb_x - TR, cy - TR), (thumb_x + TR, cy + TR)],
        fill=(255, 255, 255, 250)
    )
    draw.ellipse(
        [(thumb_x - TR + 3, cy - TR + 3), (thumb_x + TR - 3, cy + TR - 3)],
        fill=(min(255, r2 + 100), min(255, g2 + 100), min(255, b2 + 100), 200)
    )

    return thumb_x


# ── MAIN FUNCTION ─────────────────────────────────────────────────────────────

async def get_thumb(videoid, user_id, title=None, duration=None, thumbnail=None,
                    views=None, channel=None):
    if not os.path.exists("cache"):
        os.makedirs("cache")

    cache_path = f"cache/{videoid}_{user_id}.png"
    if os.path.isfile(cache_path):
        return cache_path

    try:
        if not title or not thumbnail:
            url = f"https://www.youtube.com/watch?v={videoid}"
            results = VideosSearch(url, limit=1)
            search_res = await results.next()
            if search_res and "result" in search_res and len(search_res["result"]) > 0:
                res = search_res["result"][0]
                title = res.get("title", "Unsupported Title")
                duration = res.get("duration", "Unknown")
                thumbnails = res.get("thumbnails", [{}])
                thumbnail = thumbnails[0].get("url", "").split("?")[0] if thumbnails else YOUTUBE_IMG_URL
                channel = res.get("channel", {}).get("name", "Unknown Channel")
            else:
                title, duration, thumbnail, channel = "Unsupported Title", "Unknown", YOUTUBE_IMG_URL, "Unknown Channel"

        title = re.sub(r"\W+", " ", str(title)).title()
        duration = duration or "Unknown"
        channel = channel or "Unknown Channel"

        # Download thumbnail image
        temp_thumb = f"cache/thumb{videoid}.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(temp_thumb, mode="wb") as f:
                        await f.write(await resp.read())
                else:
                    return YOUTUBE_IMG_URL

        SCALE = 2
        W, H = 1280 * SCALE, 720 * SCALE

        BOTTOM_H = 185 * SCALE
        CZ_H = H - BOTTOM_H

        canvas = Image.new("RGBA", (W, H), (10, 6, 22, 255))

        with Image.open(temp_thumb) as raw_img:
            cover_raw = raw_img.convert("RGBA")
            cover_raw = ImageEnhance.Sharpness(cover_raw).enhance(1.4)
            cover_raw = ImageEnhance.Color(cover_raw).enhance(1.3)

            dominant = get_dominant_color(cover_raw)
            palette = build_palette(dominant)
            r_d, g_d, b_d = dominant

            cover_bg = cover_raw.resize((W, CZ_H), Image.LANCZOS).convert("RGBA")
            cover_bg = cover_bg.filter(ImageFilter.GaussianBlur(28 * SCALE // 2))
            cover_bg = Image.alpha_composite(
                cover_bg, Image.new("RGBA", (W, CZ_H), (0, 0, 0, 140))
            )
            canvas.paste(cover_bg, (0, 0))

            fade = Image.new("RGBA", (W, 130 * SCALE), (0, 0, 0, 0))
            for row in range(130 * SCALE):
                a = int((row / (130 * SCALE)) ** 1.5 * 240)
                ImageDraw.Draw(fade).line([(0, row), (W, row)], fill=(10, 6, 22, a))
            canvas.alpha_composite(fade, (0, CZ_H - 65 * SCALE))

            bar_r = max(0, r_d - 160)
            bar_g = max(0, g_d - 160)
            bar_b = max(0, b_d - 150)
            bar = Image.new("RGBA", (W, BOTTOM_H + 20 * SCALE), (bar_r, bar_g, bar_b, 240))
            bar = Image.alpha_composite(
                bar, Image.new("RGBA", (W, BOTTOM_H + 20 * SCALE), (0, 0, 0, 80))
            )
            canvas.alpha_composite(bar, (0, CZ_H - 16 * SCALE))

            CV_W = 390 * SCALE
            CV_H = 320 * SCALE
            CV_LEFT = (W - CV_W) // 2
            CV_TOP = (CZ_H - CV_H) // 2 + 30 * SCALE

            cover_sq = cover_raw.resize((CV_W, CV_H), Image.LANCZOS).convert("RGBA")
            cover_sq = ImageEnhance.Sharpness(cover_sq).enhance(1.5)
            cover_sq = ImageEnhance.Contrast(cover_sq).enhance(1.1)
            rc_mask = Image.new("L", (CV_W, CV_H), 0)
            ImageDraw.Draw(rc_mask).rounded_rectangle(
                [(0, 0), (CV_W, CV_H)], radius=22 * SCALE, fill=255
            )
            cover_sq.putalpha(rc_mask)

            sh_w, sh_h = CV_W + 80 * SCALE, CV_H + 80 * SCALE
            shadow = Image.new("RGBA", (sh_w, sh_h), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).rounded_rectangle(
                [(24 * SCALE, 24 * SCALE), (sh_w - 24 * SCALE, sh_h - 24 * SCALE)],
                radius=30 * SCALE, fill=(r_d // 2, g_d // 2, b_d // 2, 180)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(22 * SCALE // 2))
            canvas.alpha_composite(shadow, (CV_LEFT - 40 * SCALE, CV_TOP - 40 * SCALE))
            canvas.alpha_composite(cover_sq, (CV_LEFT, CV_TOP))

            ring_pad = 10 * SCALE
            ring_layer = make_neon_glow_border(
                (W, H),
                (CV_LEFT - ring_pad, CV_TOP - ring_pad,
                 CV_LEFT + CV_W + ring_pad, CV_TOP + CV_H + ring_pad),
                dominant, radius=28 * SCALE, stroke=5 * SCALE, glow_layers=10
            )
            canvas.alpha_composite(ring_layer)

            border_layer = make_neon_glow_border(
                (W, H), (6 * SCALE, 6 * SCALE, W - 6 * SCALE, H - 6 * SCALE),
                dominant, radius=30 * SCALE, stroke=5 * SCALE, glow_layers=12
            )
            canvas.alpha_composite(border_layer)

            BW, BH = 210 * SCALE, 42 * SCALE
            badge = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
            p0 = palette[0]
            ImageDraw.Draw(badge).rounded_rectangle(
                [(0, 0), (BW, BH)],
                radius=BH // 2,
                fill=(max(0, p0[0] - 80), max(0, p0[1] - 80), max(0, p0[2] - 80), 210),
                outline=(min(255, p0[0] + 100), min(255, p0[1] + 100), min(255, p0[2] + 100), 220),
                width=3 * SCALE // 2
            )
            canvas.alpha_composite(badge, (28 * SCALE, 26 * SCALE))

            bot_name = unidecode(app.name)[:18]
            try:
                font_badge_tmp = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 18 * SCALE)
                txt_w = font_badge_tmp.getlength(bot_name)
            except Exception:
                txt_w = len(bot_name) * 11 * SCALE

            RBW = int(txt_w) + 36 * SCALE
            RBH = BH
            rbadge = Image.new("RGBA", (RBW, RBH), (0, 0, 0, 0))
            ImageDraw.Draw(rbadge).rounded_rectangle(
                [(0, 0), (RBW, RBH)],
                radius=RBH // 2,
                fill=(max(0, p0[0] - 80), max(0, p0[1] - 80), max(0, p0[2] - 80), 210),
                outline=(min(255, p0[0] + 100), min(255, p0[1] + 100), min(255, p0[2] + 100), 220),
                width=3 * SCALE // 2
            )
            RB_X = W - RBW - 28 * SCALE
            RB_Y = 26 * SCALE
            canvas.alpha_composite(rbadge, (RB_X, RB_Y))

            try:
                font_bold = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 32 * SCALE)
                font_badge = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 18 * SCALE)
                font_small = ImageFont.truetype("AnonXMusic/assets/font.ttf", 24 * SCALE)
                font_dur = ImageFont.truetype("AnonXMusic/assets/font.ttf", 22 * SCALE)
            except Exception:
                font_bold = font_badge = font_small = font_dur = ImageFont.load_default()

            draw = ImageDraw.Draw(canvas)

            draw.text(
                (48 * SCALE, 34 * SCALE),
                "NOW PLAYING",
                fill=(230, 235, 255, 245),
                font=font_badge
            )

            draw.text(
                (RB_X + 18 * SCALE, RB_Y + 10 * SCALE),
                bot_name,
                fill=(230, 235, 255, 245),
                font=font_badge
            )

            BAR_Y = CZ_H - 16 * SCALE
            IS = 118 * SCALE
            ICON_X = 52 * SCALE
            ICON_Y = BAR_Y + (BOTTOM_H - IS) // 2

            icon_img = cover_raw.resize((IS, IS), Image.LANCZOS).convert("RGBA")
            icon_img = ImageEnhance.Sharpness(icon_img).enhance(1.3)
            ic_mask = Image.new("L", (IS, IS), 0)
            ImageDraw.Draw(ic_mask).rounded_rectangle(
                [(0, 0), (IS, IS)], radius=16 * SCALE, fill=255
            )
            icon_img.putalpha(ic_mask)
            canvas.alpha_composite(icon_img, (ICON_X, ICON_Y))

            TEXT_X = ICON_X + IS + 22 * SCALE
            LINE1_Y = BAR_Y + 16 * SCALE
            LINE2_Y = BAR_Y + 16 * SCALE + 38 * SCALE

            draw.text((TEXT_X, LINE1_Y), clear(title, 40),
                      fill=(255, 255, 255, 250), font=font_bold)
            draw.text(
                (TEXT_X, LINE2_Y),
                f"Played by: {unidecode(app.name)}  ·  {channel[:32]}",
                fill=(175, 180, 215, 195),
                font=font_small
            )

            PROG_X0 = TEXT_X
            PROG_X1 = W - 32 * SCALE
            BAR_H_PX = 8 * SCALE
            PROG_Y = BAR_Y + BOTTOM_H - 52 * SCALE
            TIME_Y = PROG_Y + BAR_H_PX + 8 * SCALE

            draw_glowing_progress_bar(
                draw, canvas,
                PROG_X0, PROG_Y, PROG_X1, BAR_H_PX,
                thumb_frac=0.65,
                palette=palette
            )

            draw.text((PROG_X0, TIME_Y), "00:00", fill=(195, 200, 230, 210), font=font_dur)
            draw.text((PROG_X1 - 74 * SCALE, TIME_Y), str(duration)[:7], fill=(195, 200, 230, 210), font=font_dur)

        final = canvas.convert("RGB").resize((1280, 720), Image.LANCZOS)

        if os.path.exists(temp_thumb):
            try:
                os.remove(temp_thumb)
            except Exception:
                pass

        final.save(cache_path, quality=97, optimize=False)
        return cache_path

    except Exception as e:
        print(f"Thumbnail Generation Error: {e}")
        return YOUTUBE_IMG_URL
