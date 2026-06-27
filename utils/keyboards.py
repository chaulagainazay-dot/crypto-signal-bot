"""Centralised keyboard builder for Trading AI bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def kb(*rows, back: str = None, home: bool = True) -> InlineKeyboardMarkup:
    """Build InlineKeyboardMarkup.
    Each item in rows is a list of (label, callback_data) tuples.
    """
    buttons = []
    for row in rows:
        buttons.append([InlineKeyboardButton(t, callback_data=d) for t, d in row])
    nav = []
    if back:
        nav.append(InlineKeyboardButton("◀ Back", callback_data=back))
    if home:
        nav.append(InlineKeyboardButton("🏠 Menu", callback_data="menu"))
    if nav:
        buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


def kb_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="menu")]])
