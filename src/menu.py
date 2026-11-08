import pygame

# Rows are drawn and hit-tested from the same layout, so they can't drift apart.
# They split the full screen height between them, so there are no dead zones.
MENU_ITEMS = ("duration", "order", "folder", "transition", "close", "shutdown")
ROW_GAP = 6
SIDE_MARGIN = 30
TEXT_INDENT = 20

WHITE = (255, 255, 255)
GREEN = (100, 255, 100)
RED = (255, 100, 100)
BUTTON = (55, 55, 55)
BUTTON_PRESSED = (110, 110, 110)
BUTTON_WARNING = (140, 30, 30)

def row_height(height):
    return height // len(MENU_ITEMS)

def menu_item_at(y, height):
    row = y // row_height(height)
    if 0 <= row < len(MENU_ITEMS):
        return MENU_ITEMS[row]
    return None

def draw_menu(screen, font, width, height, app_state, highlight=None, confirm_shutdown=False):
    menu_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    menu_surface.fill((0, 0, 0, 220))

    order_str = "Random" if app_state.random_order else "Sequential"
    labels = {
        "duration": (f"Duration: {app_state.display_duration} seconds", WHITE),
        "order": (f"Order: {order_str}", WHITE),
        "folder": (f"Folder: {app_state.current_folder}", WHITE),
        "transition": (f"Transition: {app_state.transition_type.title()}", WHITE),
        "close": ("Close Menu", GREEN),
        "shutdown": ("Tap again to shut down" if confirm_shutdown else "Shutdown Pi",
                     WHITE if confirm_shutdown else RED),
    }

    row_h = row_height(height)
    for row, item in enumerate(MENU_ITEMS):
        box = pygame.Rect(SIDE_MARGIN, row * row_h + ROW_GAP // 2,
                          width - 2 * SIDE_MARGIN, row_h - ROW_GAP)
        if item == highlight:
            colour = BUTTON_PRESSED
        elif item == "shutdown" and confirm_shutdown:
            colour = BUTTON_WARNING
        else:
            colour = BUTTON
        pygame.draw.rect(menu_surface, colour, box, border_radius=10)

        text, text_colour = labels[item]
        rendered = font.render(text, True, text_colour)
        menu_surface.blit(rendered, (box.x + TEXT_INDENT, box.centery - rendered.get_height() // 2))

    rotated_menu = pygame.transform.rotate(menu_surface, 180)
    screen.blit(rotated_menu, (0, 0))
    pygame.display.flip()
