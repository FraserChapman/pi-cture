import os
import sys
import time
import subprocess
import traceback

def log_error(msg):
    with open('/tmp/photoframe_error.log', 'a') as f:
        f.write(f"{time.ctime()}: {msg}\n")

try:
    import pygame
    from state import AppState, DURATIONS, TRANSITIONS
    from menu import draw_menu, menu_item_at
    from web import start_web_server

    os.environ["SDL_VIDEODRIVER"] = "wayland"
    os.environ["SDL_KMSDRM_DEVICE_INDEX"] = "0"

    time.sleep(2) # Give cage time to initialize outputs
    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont(None, 40)

    # Wait for displays
    for _ in range(20):
        try:
            pygame.display.quit()
            pygame.display.init()
            if pygame.display.get_desktop_sizes():
                break
        except:
            pass
        time.sleep(0.5)

    screen = pygame.display.set_mode((800, 480), pygame.FULLSCREEN | pygame.DOUBLEBUF)
    width, height = screen.get_size()

    app_state = AppState()
    start_web_server(app_state)
    touch_start_time = 0
    shutdown_armed_until = 0

except Exception as e:
    log_error(traceback.format_exc())
    sys.exit(1)

SHUTDOWN_CONFIRM_SECONDS = 3
TAP_FLASH_MS = 150

def redraw_menu(highlight=None):
    confirm_shutdown = time.time() < shutdown_armed_until
    draw_menu(screen, font, width, height, app_state, highlight, confirm_shutdown)

def flash_menu_row(item):
    # Briefly show the tapped row as pressed so the tap is obvious
    redraw_menu(highlight=item)
    pygame.time.wait(TAP_FLASH_MS)
    redraw_menu()

def show_image(index, transition="cut"):
    if not app_state.images:
        screen.fill((0, 0, 0))
        pygame.display.flip()
        return
        
    try:
        img = pygame.image.load(app_state.images[index]).convert()
    except Exception as e:
        log_error(f"Failed to load image: {e}")
        return
    
    img_rect = img.get_rect()
    screen_aspect = width / height
    img_aspect = img_rect.width / img_rect.height
    
    if img_aspect > screen_aspect:
        new_width = width
        new_height = int(width / img_aspect)
    else:
        new_height = height
        new_width = int(height * img_aspect)
        
    img = pygame.transform.scale(img, (new_width, new_height))
    img = pygame.transform.rotate(img, 180)
    
    x = (width - new_width) // 2
    y = (height - new_height) // 2
    
    new_surface = pygame.Surface((width, height))
    new_surface.fill((0, 0, 0))
    new_surface.blit(img, (x, y))
    
    if transition == "cut":
        screen.blit(new_surface, (0, 0))
        pygame.display.flip()
    elif transition == "fade":
        old_surface = screen.copy()
        frames = 30
        for alpha in range(0, 256, 256 // frames):
            screen.blit(old_surface, (0, 0))
            new_surface.set_alpha(alpha)
            screen.blit(new_surface, (0, 0))
            pygame.display.flip()
            pygame.time.delay(1000 // frames)
        new_surface.set_alpha(255)
        screen.blit(new_surface, (0, 0))
        pygame.display.flip()
    elif transition == "slide":
        old_surface = screen.copy()
        frames = 30
        for i in range(frames):
            offset = int(width * (i / frames))
            screen.blit(old_surface, (offset, 0))
            screen.blit(new_surface, (offset - width, 0))
            pygame.display.flip()
            pygame.time.delay(1000 // frames)
        screen.blit(new_surface, (0, 0))
        pygame.display.flip()

try:
    if app_state.images:
        show_image(app_state.current_index, transition="cut")

    pygame.mouse.set_visible(False)
    running = True

    while running:
        # Handle web interface events
        if app_state.web_settings_updated:
            app_state.refresh_folders()
            app_state.refresh_images()
            app_state.current_index = 0
            if app_state.mode == "SLIDESHOW":
                show_image(app_state.current_index, transition="cut")
                app_state.last_change_time = time.time()
            else:
                redraw_menu()
            app_state.web_settings_updated = False
            
        if app_state.web_action:
            if app_state.web_action == 'prev' and app_state.mode == "SLIDESHOW":
                app_state.current_index = app_state.get_prev_index()
                show_image(app_state.current_index, transition=app_state.transition_type)
                app_state.last_change_time = time.time()
            elif app_state.web_action == 'next' and app_state.mode == "SLIDESHOW":
                app_state.current_index = app_state.get_next_index()
                show_image(app_state.current_index, transition=app_state.transition_type)
                app_state.last_change_time = time.time()
            elif app_state.web_action == 'reload':
                app_state.refresh_images()
                if app_state.current_index >= len(app_state.images):
                    app_state.current_index = 0
                if app_state.mode == "SLIDESHOW":
                    show_image(app_state.current_index, transition="cut")
            app_state.web_action = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                touch_start_time = time.time()
            elif event.type == pygame.MOUSEBUTTONUP:
                x, y = event.pos
                real_x = width - x
                real_y = height - y
                press_duration = time.time() - touch_start_time
                
                if app_state.mode == "SLIDESHOW":
                    if press_duration > 1.0:
                        app_state.refresh_folders()
                        app_state.mode = "MENU"
                        redraw_menu()
                    else:
                        if app_state.images:
                            if real_x < width // 2:
                                app_state.current_index = app_state.get_prev_index()
                            else:
                                app_state.current_index = app_state.get_next_index()
                            show_image(app_state.current_index, transition=app_state.transition_type)
                            app_state.last_change_time = time.time()
                            
                            pygame.event.clear()
                elif app_state.mode == "MENU":
                    item = menu_item_at(real_y, height)
                    if item != "shutdown":
                        shutdown_armed_until = 0
                    if item == "duration":
                        d_idx = DURATIONS.index(app_state.display_duration) if app_state.display_duration in DURATIONS else -1
                        app_state.display_duration = DURATIONS[(d_idx + 1) % len(DURATIONS)]
                        app_state.save_settings()
                        flash_menu_row(item)
                    elif item == "order":
                        app_state.random_order = not app_state.random_order
                        app_state.save_settings()
                        flash_menu_row(item)
                    elif item == "folder":
                        if app_state.available_folders:
                            f_idx = app_state.available_folders.index(app_state.current_folder)
                            app_state.current_folder = app_state.available_folders[(f_idx + 1) % len(app_state.available_folders)]
                            app_state.refresh_images()
                            app_state.current_index = 0
                            app_state.save_settings()
                        flash_menu_row(item)
                    elif item == "transition":
                        t_idx = TRANSITIONS.index(app_state.transition_type)
                        app_state.transition_type = TRANSITIONS[(t_idx + 1) % len(TRANSITIONS)]
                        app_state.save_settings()
                        flash_menu_row(item)
                    elif item == "close":
                        flash_menu_row(item)
                        app_state.mode = "SLIDESHOW"
                        show_image(app_state.current_index, transition="cut")
                        app_state.last_change_time = time.time()
                    elif item == "shutdown":
                        # Needs a second tap, so a stray touch can't power it off
                        if time.time() < shutdown_armed_until:
                            pygame.quit()
                            subprocess.run(["sudo", "poweroff"])
                            sys.exit()
                        shutdown_armed_until = time.time() + SHUTDOWN_CONFIRM_SECONDS
                        redraw_menu()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        if shutdown_armed_until and time.time() >= shutdown_armed_until:
            shutdown_armed_until = 0
            if app_state.mode == "MENU":
                redraw_menu()

        if app_state.mode == "SLIDESHOW":
            if time.time() - app_state.last_change_time > app_state.display_duration and app_state.images:
                app_state.current_index = app_state.get_next_index()
                show_image(app_state.current_index, transition=app_state.transition_type)
                app_state.last_change_time = time.time()
                pygame.event.clear()

        pygame.time.Clock().tick(30)

    pygame.quit()
    sys.exit()
except Exception as e:
    log_error(traceback.format_exc())
    sys.exit(1)