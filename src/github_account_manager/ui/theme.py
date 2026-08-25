"""UI Theme constants, color palettes (Light & Dark mode tuple support), and typography across OSes."""
import sys

# Color palettes (Light Mode Color, Dark Mode Color)

# Backgrounds
BG_APP = ("#f6f8fa", "#0d1117")
BG_SIDEBAR = ("#ffffff", "#161b22")
BG_CARD = ("#ffffff", "#21262d")
BG_CARD_HOVER = ("#f3f4f6", "#282e37")
BG_INSET = ("#f3f4f6", "#161b22")
BORDER_COLOR = ("#d0d7de", "#30363d")

# Neutral Buttons
BTN_SECONDARY_BG = ("#eaeef2", "#30363d")
BTN_SECONDARY_HOVER = ("#dbe0e6", "#3e4752")
BTN_SECONDARY_TEXT = ("#24292f", "#f0f6fc")

# Accent Colors
ACCENT_GREEN = ("#1f883d", "#238636")
ACCENT_GREEN_HOVER = ("#1a7f37", "#2ea043")

ACCENT_BLUE = ("#0969da", "#1f6feb")
ACCENT_BLUE_HOVER = ("#0860ca", "#388bfd")

ACCENT_RED = ("#cf222e", "#da3633")
ACCENT_RED_HOVER = ("#b62324", "#f85149")

ACCENT_ORANGE = ("#9a6700", "#d29922")

# Text Colors
TEXT_PRIMARY = ("#1f2328", "#f0f6fc")
TEXT_SECONDARY = ("#57606a", "#8b949e")
TEXT_MUTED = ("#656d76", "#7d8590")

# Platform-aware Font Families
if sys.platform == "darwin":
    _SYS_FONT = "SF Pro Text"
    _MONO_FONT = "Menlo"
elif sys.platform.startswith("linux"):
    _SYS_FONT = "Ubuntu"
    _MONO_FONT = "Ubuntu Mono"
else:
    _SYS_FONT = "Segoe UI"
    _MONO_FONT = "Consolas"

# Typography
FONT_TITLE = (_SYS_FONT, 20, "bold")
FONT_HEADING = (_SYS_FONT, 16, "bold")
FONT_SUBHEADING = (_SYS_FONT, 14, "bold")
FONT_BODY = (_SYS_FONT, 12)
FONT_BODY_BOLD = (_SYS_FONT, 12, "bold")
FONT_SMALL = (_SYS_FONT, 11)
FONT_SMALL_BOLD = (_SYS_FONT, 11, "bold")
FONT_MONO = (_MONO_FONT, 12)
FONT_MONO_SMALL = (_MONO_FONT, 11)