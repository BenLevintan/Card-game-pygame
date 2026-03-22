import pygame
import random
import math
import config

class Joker(pygame.sprite.Sprite):
    def __init__(self, key, scale=1.0):
        super().__init__()
        data = config.JOKER_DATA[key]
        
        self.key = key
        self.name = data['name']
        self.cost = data['cost']
        self.desc = data['desc']
        self.sell_price = self.cost // 2
        self.is_selected = False
        
        try:
            orig = pygame.image.load(data['file']).convert_alpha()
            w, h = orig.get_size()
            self.orig_image = pygame.transform.smoothscale(orig, (int(w*scale), int(h*scale)))
        except:
            self.orig_image = pygame.Surface((int(config.JOKER_WIDTH), int(350 * scale)), pygame.SRCALPHA)
            self.orig_image.fill((100, 0, 100))
            
        self.image = self.orig_image
        self.rect = self.image.get_rect()
        
        self.target_x = 0
        self.target_y = 0
        self.vel_x = 0
        self.vel_y = 0
        self._phys_x = 0
        self._phys_y = 0
        self.float_phase = random.uniform(0, 6.28)
        self.rot_phase = random.uniform(0, 6.28)
        self.timer = 0.0
        self.angle = 0

    def update(self, delta_time):
        self.timer += delta_time
        dx = self.target_x - self._phys_x
        dy = self.target_y - self._phys_y
        self.vel_x = (self.vel_x + dx * config.STIFFNESS) * config.DAMPING
        self.vel_y = (self.vel_y + dy * config.STIFFNESS) * config.DAMPING
        self._phys_x += self.vel_x
        self._phys_y += self.vel_y
        
        float_offset = math.sin(self.timer * config.FLOAT_SPEED + self.float_phase) * config.FLOAT_RANGE
        self.angle = math.sin(self.timer * config.JOKER_ROT_SPEED + self.rot_phase) * config.JOKER_ROT_RANGE
        
        self.image = pygame.transform.rotate(self.orig_image, self.angle)
        self.rect = self.image.get_rect(center=(self._phys_x, self._phys_y + float_offset))

class Pack(pygame.sprite.Sprite):
    def __init__(self, scale=1.0):
        super().__init__()
        self.name = "Standard Pack"
        self.desc = "Choose 1 of 2 modifiers\nfor selected cards."
        self.cost = config.PACK_COST
        self.is_selected = False
        
        self.image = pygame.Surface((int(config.JOKER_WIDTH), int(350 * scale)), pygame.SRCALPHA)
        self.image.fill((200, 50, 50))
        self.rect = self.image.get_rect()

class Card(pygame.sprite.Sprite):
    def __init__(self, suit, rank, scale=1):
        super().__init__()
        self.suit = suit
        self.rank = rank
        
        if rank in ['J', 'Q', 'K', 'A']:
            if rank == 'J': self.value = 11
            elif rank == 'Q': self.value = 12
            elif rank == 'K': self.value = 13
            elif rank == 'A': self.value = 14
        else:
            self.value = int(rank)
            
        self.color_type = 'Red' if suit in ['Hearts', 'Diamonds'] else 'Black'
        self.is_selected = False
        self.modifier = None 
        
        width, height = int(config.CARD_WIDTH), int(config.CARD_HEIGHT)
        
        # =========================================================
        # PRETTIER PYGAME PROCEDURAL CARDS
        # =========================================================
        self.orig_image = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(self.orig_image, (255, 255, 255), (0, 0, width, height), border_radius=10)
        pygame.draw.rect(self.orig_image, (50, 50, 50), (0, 0, width, height), 2, border_radius=10)
        
        # Load fonts (using system fonts that support symbols)
        pygame.font.init()
        # Pygbag Fix: Requesting non-existent system fonts silently crashes WASM font rendering. Use default (None).
        font_small = pygame.font.SysFont(None, 28, bold=True)
        font_large = pygame.font.SysFont(None, 65)
        
        text_color = (220, 30, 30) if self.color_type == 'Red' else (30, 30, 30)
        
        # Unicode Card Suits
        suit_symbols = {'Hearts': '♥', 'Diamonds': '♦', 'Clubs': '♣', 'Spades': '♠'}
        symbol = suit_symbols.get(suit, suit[0])
        
        # Render Text
        rank_surf = font_small.render(rank, True, text_color)
        sym_surf_small = font_small.render(symbol, True, text_color)
        sym_surf_large = font_large.render(symbol, True, text_color)
        
        # Draw Top-Left Corner
        self.orig_image.blit(rank_surf, (10, 8))
        self.orig_image.blit(sym_surf_small, (10, 32))
        
        # Draw Center Symbol
        cx = width // 2 - sym_surf_large.get_width() // 2
        cy = height // 2 - sym_surf_large.get_height() // 2
        self.orig_image.blit(sym_surf_large, (cx, cy))
        
        # Draw Bottom-Right Corner (Flipped)
        br_surf = pygame.Surface((40, 60), pygame.SRCALPHA)
        br_surf.blit(rank_surf, (0, 0))
        br_surf.blit(sym_surf_small, (0, 24))
        br_surf = pygame.transform.rotate(br_surf, 180)
        self.orig_image.blit(br_surf, (width - br_surf.get_width() - 5, height - br_surf.get_height() - 5))
        # =========================================================

        self.image = self.orig_image
        self.rect = self.image.get_rect()
        
        self.target_x = 0
        self.target_y = 0
        self.vel_x = 0
        self.vel_y = 0
        self._phys_x = 0
        self._phys_y = 0
        self.should_despawn = False 
        self.is_spasming = False 
        self.float_phase = random.uniform(0, 6.28)
        self.timer = 0.0
        self.alpha = 255

    def update(self, delta_time):
        self.timer += delta_time
        
        if self.is_spasming:
            cx = self._phys_x + random.uniform(-15, 15)
            cy = self._phys_y + random.uniform(-15, 15)
            self.alpha = max(0, self.alpha - 255 * delta_time)
            
            self.image = self.orig_image.copy()
            self.image.set_alpha(int(self.alpha))
            self.rect = self.image.get_rect(center=(cx, cy))
            
            if self.alpha <= 0:
                self.kill()
                self.is_spasming = False
                self.alpha = 255
            return 

        dx = self.target_x - self._phys_x
        dy = self.target_y - self._phys_y
        self.vel_x = (self.vel_x + dx * config.STIFFNESS) * config.DAMPING
        self.vel_y = (self.vel_y + dy * config.STIFFNESS) * config.DAMPING
        self._phys_x += self.vel_x
        self._phys_y += self.vel_y

        if self.should_despawn:
            self.rect.center = (self._phys_x, self._phys_y)
            if (self.rect.centery > config.SCREEN_HEIGHT + 200 or self.rect.centery < -200):
                self.kill()
        else:
            float_offset = math.sin(self.timer * config.FLOAT_SPEED + self.float_phase) * config.FLOAT_RANGE
            self.rect.center = (self._phys_x, self._phys_y + float_offset)

    def draw_modifier(self, screen):
        if self.modifier:
            data = config.MODIFIER_DATA[self.modifier]
            pygame.draw.rect(screen, data['color'], self.rect, 4, border_radius=8)
            
            font = pygame.font.SysFont(None, 20, bold=True)
            text_surf = font.render(data['name'][:4], True, data['color'])
            
            # Add a slight dark background to the text so it's readable
            bg_rect = text_surf.get_rect(center=(self.rect.centerx, self.rect.centery + 40))
            pygame.draw.rect(screen, (20, 20, 20), bg_rect.inflate(8, 4), border_radius=3)
            screen.blit(text_surf, bg_rect)