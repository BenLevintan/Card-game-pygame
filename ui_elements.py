import pygame
import config
import sys
import random

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

_shadow_cache = {}

class TextButton:
    def __init__(self, cx, cy, width, height, text, text_color=config.COLOR_WHITE):
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (cx, cy)
        self.text = text 
        self.base_color = config.COLOR_BTN_DEFAULT
        self.highlight_color = config.COLOR_BTN_HOVER
        self.text_color = text_color
        self.is_hovered = False
        self.visible = True
        self.active = True
        self.is_winning_play = False
        self.sparks = []
        
        # Animation properties
        self.current_y_offset = 0.0
        self.velocity_y = 0.0
        self.last_time = pygame.time.get_ticks()

    def draw(self, surface):
        current_time = pygame.time.get_ticks()
        if not self.visible: 
            self.last_time = current_time
            return

        # Calculate delta time for animation
        dt = (current_time - self.last_time) / 1000.0
        self.last_time = current_time
        dt = min(dt, 0.05)  # Cap delta time to prevent physics explosions on lag spikes

        # Target offset: -6 when hovered/active, 0 otherwise
        target_y_offset = -6.0 if (self.is_hovered and self.active) else 0.0
        
        # Spring physics for overshoot and bounce
        stiffness = 250.0
        damping = 15.0
        
        acceleration = stiffness * (target_y_offset - self.current_y_offset) - damping * self.velocity_y
        self.velocity_y += acceleration * dt
        self.current_y_offset += self.velocity_y * dt

        # -- Sparks update and draw (drawn behind the button) --
        if self.is_winning_play and self.active:
            for _ in range(3):
                sx = self.rect.centerx + random.uniform(-self.rect.width/2.5, self.rect.width/2.5)
                sy = self.rect.centery + random.uniform(-self.rect.height/2.5, self.rect.height/2.5)
                vx = random.uniform(-150, 150)
                vy = random.uniform(-250, -50)
                lifetime = random.uniform(0.2, 0.6)
                self.sparks.append([sx, sy, vx, vy, lifetime, lifetime])

        new_sparks = []
        for spark in self.sparks:
            sx, sy, vx, vy, lt, max_lt = spark
            sx += vx * dt
            sy += vy * dt
            vy += 600 * dt # gravity
            lt -= dt
            if lt > 0:
                new_sparks.append([sx, sy, vx, vy, lt, max_lt])
                spark_color = (255, random.randint(150, 255), 0)
                pygame.draw.rect(surface, spark_color, (int(sx), int(sy), 4, 4))
        self.sparks = new_sparks

        if not self.active:
            draw_color = (100, 100, 100) 
        elif self.is_hovered:
            draw_color = self.highlight_color
        else:
            draw_color = self.base_color

        draw_rect = self.rect.copy()
        draw_rect.y += round(self.current_y_offset)
        
        if self.is_winning_play and self.active:
            draw_rect.x += random.randint(-4, 4)
            draw_rect.y += random.randint(-4, 4)

        is_animating = abs(self.current_y_offset) > 0.1 or abs(self.velocity_y) > 0.1
        if (self.is_hovered and self.active) or is_animating or (self.is_winning_play and self.active):
            size = (draw_rect.width, draw_rect.height)
            if size not in _shadow_cache:
                shadow_surf = pygame.Surface(size, pygame.SRCALPHA)
                shadow_surf.fill(config.COLOR_SHADOW)
                _shadow_cache[size] = shadow_surf
                
            shadow_surf = _shadow_cache[size]
            surface.blit(shadow_surf, (draw_rect.x + 5, draw_rect.y + 5))

        pygame.draw.rect(surface, draw_color, draw_rect)
        pygame.draw.rect(surface, config.COLOR_WHITE, draw_rect, 2)

        # Pygame Multiline centering
        lines = self.text.split('\n')
        line_height = FONT_14.get_linesize()
        start_y = draw_rect.centery - (len(lines) * line_height) / 2
        
        for i, line in enumerate(lines):
            text_surf = FONT_14.render(line, True, self.text_color)
            text_rect = text_surf.get_rect(center=(draw_rect.centerx, start_y + (i * line_height) + line_height/2))
            surface.blit(text_surf, text_rect)

    def check_mouse_hover(self, x, y):
        if not self.visible: return
        self.is_hovered = self.rect.collidepoint(x, y)

    def is_clicked(self, x, y):
        return self.visible and self.active and self.is_hovered

def draw_shadows(surface, sprite_list):
    """ Simplified Pygame drop shadow """
    screen_rect = surface.get_rect().inflate(100, 100)
    for sprite in sprite_list:
        if not screen_rect.colliderect(sprite.rect):
            continue
            
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
            self.pixel_scale = 1.15
            sw, sh = int(width / self.pixel_scale), int(height / self.pixel_scale)
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
            self.small_combined.blit(self.small_red, (0, 0))
            self.small_combined.blit(self.small_cyan, (shift_amount, 0), special_flags=pygame.BLEND_RGB_ADD)
            
            # --- 3. Scale back up directly onto the screen (Pixelation step 2) ---
            pygame.transform.scale(self.small_combined, screen.get_size(), screen)
        except Exception:
            pass # If shaders fail in browser, silently ignore them so the game loop survives
        
        # --- 4. Moving Scanlines ---
        screen.blit(self.scanline_surf, (0, int(self.y_offset) - self.scanline_spacing))
        
        # --- 5. Vignette ---
        screen.blit(self.vignette, (0, 0))

class VolumeControl:
    def __init__(self, x, y, width=100, height=10, initial_vol=0.5):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        self.mute_rect = pygame.Rect(x, y - 10, 20, 20)
        self.slider_rect = pygame.Rect(x + 30, y - height//2, width, height)
        
        self.volume = initial_vol
        self.is_muted = False
        self.is_dragging = False

    def draw(self, surface):
        icon_color = config.COLOR_RED if self.is_muted else config.COLOR_WHITE
        pygame.draw.rect(surface, icon_color, self.mute_rect, 2, border_radius=4)
        
        pygame.draw.polygon(surface, icon_color, [(self.x+4, self.y), (self.x+8, self.y-5), (self.x+8, self.y+5)])
        if self.is_muted:
            pygame.draw.line(surface, config.COLOR_RED, (self.x+12, self.y-5), (self.x+18, self.y+5), 2)
            pygame.draw.line(surface, config.COLOR_RED, (self.x+18, self.y-5), (self.x+12, self.y+5), 2)
        else:
            pygame.draw.line(surface, icon_color, (self.x+12, self.y-3), (self.x+12, self.y+3), 2)
            pygame.draw.line(surface, icon_color, (self.x+16, self.y-6), (self.x+16, self.y+6), 2)

        pygame.draw.rect(surface, (50, 50, 50), self.slider_rect, border_radius=4)
        if not self.is_muted:
            fill_width = int(self.width * self.volume)
            fill_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y, fill_width, self.slider_rect.height)
            pygame.draw.rect(surface, config.COLOR_GREEN, fill_rect, border_radius=4)
            pygame.draw.circle(surface, config.COLOR_WHITE, (self.slider_rect.x + fill_width, self.slider_rect.centery), self.height)

    def update_volume_from_mouse(self, x):
        rel_x = x - self.slider_rect.x
        self.volume = max(0.0, min(1.0, rel_x / self.width))
        if self.volume > 0:
            self.is_muted = False
        elif self.volume == 0:
            self.is_muted = True

    def handle_mouse_down(self, x, y):
        if self.mute_rect.collidepoint(x, y):
            self.is_muted = not self.is_muted
            if not self.is_muted and self.volume == 0:
                self.volume = 0.5
            return True
        elif self.slider_rect.collidepoint(x, y) or self.slider_rect.inflate(0, 10).collidepoint(x, y):
            self.is_dragging = True
            self.update_volume_from_mouse(x)
            return True
        return False
        
    def handle_mouse_up(self, x, y):
        was_dragging = self.is_dragging
        self.is_dragging = False
        return was_dragging
        
    def handle_mouse_motion(self, x, y):
        if self.is_dragging:
            self.update_volume_from_mouse(x)
            return True
        return False
        
    def get_actual_volume(self):
        return 0.0 if self.is_muted else self.volume