"""Professional open-licence fonts (Google Fonts, SIL OFL 1.1 - free for commercial video use; licence in fonts/OFL.txt)."""
import os
from PIL import ImageFont
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONTS = {'anton': ('Anton-Regular.ttf', None), 'bebas': ('BebasNeue-Regular.ttf', None), 'bungee': ('Bungee-Regular.ttf', None),
         'playfair': ('PlayfairDisplay[wght].ttf', 900), 'oswald': ('Oswald[wght].ttf', 600), 'oswald_b': ('Oswald[wght].ttf', 700),
         'montserrat': ('Montserrat[wght].ttf', 800), 'montserrat_sb': ('Montserrat[wght].ttf', 600), 'poppins': ('Poppins-ExtraBold.ttf', None),
         'poppins_sb': ('Poppins-SemiBold.ttf', None), 'baloo': ('Baloo2[wght].ttf', 800), 'teko': ('Teko[wght].ttf', 600), 'patrickhand': ('PatrickHand-Regular.ttf', None), 'gochi': ('GochiHand-Regular.ttf', None),
         'caveat': ('Caveat[wght].ttf', 700)}


def path(k): return os.path.join(D, FONTS[k][0])


def kw(k):
    """kwargs for city.sign / sign_mat"""
    return dict(font=path(k), wght=FONTS[k][1])


def font(k, size):
    f = ImageFont.truetype(path(k), int(size))
    if FONTS[k][1]:
        try: f.set_variation_by_axes([FONTS[k][1]])
        except Exception: pass
    return f
