import pygame
import config
import sys

FONT_14 = None
FONT_12 = None
FONT_16 = None
FONT_20 = None

def init_fonts():
    global FONT_14, FONT_12, FONT_16, FONT_20
    if FONT_14 is None:
        pygame.font.init()
        FONT_14 = pygame.font.SysFont(None, 24, bold=True)
        FONT_12 = pygame.font.SysFont(None, 20)
        FONT_16 = pygame.font.SysFont(None, 28)
        FONT_20 = pygame.font.SysFont(None, 34, bold=True)

class TextButton:
    def __init__(self, cx, cy, width, height, text, color=config.COLOR_BTN_DEFAULT, text_color=config.COLOR_WHITE):
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (cx, cy)
        self.text = text 
        self.base_color = color
        self.highlight_color = config.COLOR_BTN_HOVER
        self.text_color = text_color
        self.is_hovered = False
        self.visible = True
        self.active = True

    def draw(self, surface):
        if not self.visible: return

        if not self.active:
            draw_color = (100, 100, 100) 
        elif self.is_hovered:
            draw_color = self.highlight_color
        else:
            draw_color = self.base_color

        pygame.draw.rect(surface, draw_color, self.rect)
        pygame.draw.rect(surface, config.COLOR_WHITE, self.rect, 2)

        # Pygame Multiline centering
        lines = self.text.split('\n')
        line_height = FONT_14.get_linesize()
        start_y = self.rect.centery - (len(lines) * line_height) / 2
        
        for i, line in enumerate(lines):
            text_surf = FONT_14.render(line, True, self.text_color)
            text_rect = text_surf.get_rect(center=(self.rect.centerx, start_y + (i * line_height) + line_height/2))
            surface.blit(text_surf, text_rect)

    def check_mouse_hover(self, x, y):
        if not self.visible: return
        self.is_hovered = self.rect.collidepoint(x, y)

    def is_clicked(self, x, y):
        return self.visible and self.active and self.is_hovered

_shadow_cache = {}

def draw_shadows(surface, sprite_list):
    """ Simplified Pygame drop shadow """
    for sprite in sprite_list:
        shadow_rect = sprite.rect.copy()
        
        offset_x = 5
        offset_y = 5
        
        if getattr(sprite, 'is_selected', False):
            offset_x += 5
            offset_y += 15
            
        shadow_rect.x += offset_x
        shadow_rect.y += offset_y # Shadow goes down in Pygame
        
        # Optimize memory by reusing shadow surfaces
        size = (shadow_rect.width, shadow_rect.height)
        if size not in _shadow_cache:
            shadow_surf = pygame.Surface(size, pygame.SRCALPHA)
            shadow_surf.fill(config.COLOR_SHADOW)
            _shadow_cache[size] = shadow_surf
            
        shadow_surf = _shadow_cache[size]
        
        if hasattr(sprite, 'angle') and sprite.angle != 0:
            shadow_surf = pygame.transform.rotate(shadow_surf, sprite.angle)
            shadow_rect = shadow_surf.get_rect(center=shadow_rect.center)
            
        surface.blit(shadow_surf, shadow_rect)

def draw_tooltip(surface, hovered_joker, mouse_x, mouse_y):
    if not hovered_joker:
        return

    width, height = 240, 80
    tip_x = mouse_x + 20
    tip_y = mouse_y - 20

    if tip_x + width > config.SCREEN_WIDTH:
        tip_x = mouse_x - width - 20
    
    bg_rect = pygame.Rect(tip_x, tip_y - height, width, height)
    pygame.draw.rect(surface, config.COLOR_TOOLTIP_BG, bg_rect)
    pygame.draw.rect(surface, config.COLOR_WHITE, bg_rect, 1)
    
    name_surf = FONT_14.render(hovered_joker.name, True, config.COLOR_GOLD)
    surface.blit(name_surf, (tip_x + 10, tip_y - height + 10))
    
    desc_surf = FONT_12.render(hovered_joker.desc, True, config.COLOR_WHITE)
    surface.blit(desc_surf, (tip_x + 10, tip_y - height + 40))


# --- NEW: CRT Overlay Class ---
class CRTOverlay:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # 1. Create the scanline surface (slightly taller for scrolling)
        self.scanline_spacing = 8
        self.scanline_surf = pygame.Surface((width, height + self.scanline_spacing), pygame.SRCALPHA)
        
        for y in range(0, height + self.scanline_spacing, self.scanline_spacing):
            pygame.draw.line(self.scanline_surf, (0, 0, 0, 60), (0, y), (width, y), 4)
            
        # 2. Draw a subtle darkened vignette around the edges
        self.vignette = pygame.Surface((width, height), pygame.SRCALPHA)
        self.vignette.fill((0, 0, 0, 0)) # Explicitly clear WebGL garbage memory
        thickness = 240
        for i in range(thickness):
            alpha = int(150 * (1.0 - (i / thickness)))
            pygame.draw.rect(self.vignette, (0, 0, 0, alpha), (i, i, width - i*2, height - i*2), 1)
        
        self.y_offset = 0.0
        
        # --- Pre-allocated Surfaces for Shaders (Performance Optimization) ---
        if sys.platform not in ("emscripten", "wasi"):
            self.pixel_scale = 1.5
            sw, sh = width // self.pixel_scale, height // self.pixel_scale
            self.small_surf = pygame.Surface((sw, sh)).convert()
            self.small_red = pygame.Surface((sw, sh)).convert()
            self.small_cyan = pygame.Surface((sw, sh)).convert()
            self.small_combined = pygame.Surface((sw, sh)).convert()

    def update(self, delta_time):
        # Animate scanlines moving downwards
        self.y_offset += 8 * delta_time
        if self.y_offset >= self.scanline_spacing:
            self.y_offset -= self.scanline_spacing

    def draw(self, screen):
        """ Draws the overlay onto the target screen """
        # --- WebAssembly / Pygbag Fallback ---
        if sys.platform in ("emscripten", "wasi"):
            screen.blit(self.scanline_surf, (0, int(self.y_offset) - self.scanline_spacing))
            screen.blit(self.vignette, (0, 0))
            return
            
        try:
            # --- 1. Scale down (Pixelation step 1) ---
            pygame.transform.scale(screen, self.small_surf.get_size(), self.small_surf)
            
            # --- 2. Chromatic Aberration applied to SMALL surface ---
            self.small_red.blit(self.small_surf, (0, 0))
            self.small_red.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
            
            self.small_cyan.blit(self.small_surf, (0, 0))
            self.small_cyan.fill((0, 255, 255), special_flags=pygame.BLEND_RGB_MULT)
            
            self.small_combined.fill((0, 0, 0))
            shift_amount = 1 
            self.small_combined.blit(self.small_red, (-shift_amount, 0))
            self.small_combined.blit(self.small_cyan, (shift_amount, 0), special_flags=pygame.BLEND_RGB_ADD)
            
            # --- 3. Scale back up directly onto the screen (Pixelation step 2) ---
            pygame.transform.scale(self.small_combined, screen.get_size(), screen)
        except Exception:
            pass # If shaders fail in browser, silently ignore them so the game loop survives
        
        # --- 4. Moving Scanlines ---
        screen.blit(self.scanline_surf, (0, int(self.y_offset) - self.scanline_spacing))
        
        # --- 5. Vignette ---
        screen.blit(self.vignette, (0, 0))