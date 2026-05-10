import os
import json
import random
import pygame
import config
import sprites
import ui_elements

class AudioManager:
    """ Handles all sound effects and music cross-fading via Pygame Mixer """
    def __init__(self):
        pygame.mixer.init()
        try:
            self.bg_music = pygame.mixer.Sound(config.MUSIC_BG)
            self.store_music = pygame.mixer.Sound(config.MUSIC_STORE)
            self.game_over_music = pygame.mixer.Sound(config.MUSIC_GAME_OVER)
            self.card_sound = pygame.mixer.Sound(config.SOUND_CARD)
            self.play_hand_sound = pygame.mixer.Sound(config.SOUND_PLAY_HAND)
            self.buy_joker_sound = pygame.mixer.Sound(config.SOUND_BUY_JOKER) 
            self.mod_sound = pygame.mixer.Sound(config.SOUND_MOD)             
        except Exception as e:
            print(f"Warning: Audio file missing. {e}")
            self.bg_music, self.store_music, self.game_over_music = None, None, None
            self.card_sound, self.play_hand_sound, self.buy_joker_sound, self.mod_sound = None, None, None, None

        self.bg_channel = pygame.mixer.Channel(0)
        self.store_channel = pygame.mixer.Channel(1)
        self.go_channel = pygame.mixer.Channel(2)
        
        self.base_volume = 0.5   
        self.bg_target_volume = self.base_volume
        self.store_target_volume = 0.0
        self.game_over_target_volume = 0.0
        
        self.fade_speed = 0.8    

        self.set_master_volume(self.base_volume)

    def set_master_volume(self, volume):
        self.base_volume = volume
        
        if self.bg_target_volume > 0: self.bg_target_volume = self.base_volume
        if self.store_target_volume > 0: self.store_target_volume = self.base_volume
        if self.game_over_target_volume > 0: self.game_over_target_volume = self.base_volume
        
        for s in [self.card_sound, self.play_hand_sound, self.buy_joker_sound, self.mod_sound]:
            if s: s.set_volume(volume)

    def play_card_sound(self):
        if self.card_sound: self.card_sound.play() # Pygame doesn't natively do random pitch easily

    def play_hand_fx(self):
        if self.play_hand_sound: self.play_hand_sound.play()

    def play_buy_joker_fx(self):
        if self.buy_joker_sound: self.buy_joker_sound.play()
            
    def play_mod_fx(self):
        if self.mod_sound: self.mod_sound.play()

    def start_bg_music(self):
        self.bg_target_volume = self.base_volume
        self.store_target_volume = 0.0
        self.game_over_target_volume = 0.0
        if self.bg_music:
            self.bg_channel.play(self.bg_music, loops=-1)
            self.bg_channel.set_volume(0.0)

    def enter_store(self):
        self.bg_target_volume = 0.0
        self.store_target_volume = self.base_volume
        self.game_over_target_volume = 0.0
        if self.store_music:
            self.store_channel.play(self.store_music, loops=-1)
            self.store_channel.set_volume(0.0)

    def exit_store(self):
        self.start_bg_music()

    def enter_game_over(self):
        self.bg_target_volume = 0.0
        self.store_target_volume = 0.0
        self.game_over_target_volume = self.base_volume
        if self.game_over_music:
            self.go_channel.play(self.game_over_music, loops=-1)
            self.go_channel.set_volume(0.0)

    def update(self, delta_time):
        def fade_channel(channel, target):
            if channel.get_busy():
                vol = channel.get_volume()
                if vol < target: channel.set_volume(min(target, vol + self.fade_speed * delta_time))
                elif vol > target: channel.set_volume(max(target, vol - self.fade_speed * delta_time))
        
        fade_channel(self.bg_channel, self.bg_target_volume)
        fade_channel(self.store_channel, self.store_target_volume)
        fade_channel(self.go_channel, self.game_over_target_volume)

class DeckManager:
    def __init__(self):
        self.master_deck = []
        self.draw_pile = []
        self.discard_pile = []
        self._create_initial_deck()

    def _create_initial_deck(self):
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        for suit in suits:
            for rank in ranks:
                card = sprites.Card(suit, rank, config.CARD_SCALE)
                self.master_deck.append(card)

    def start_round(self, visual_card_list):
        self.draw_pile = [c for c in self.master_deck if c.modifier != "destroy"]
        self.discard_pile = []
        random.shuffle(self.draw_pile)
        
        for card in self.draw_pile:
            card.should_despawn = False
            card.is_spasming = False
            card.is_selected = False
            card._phys_x = config.SCREEN_WIDTH + 200
            card._phys_y = config.DRAWN_CARD_Y
            card.target_x = config.SCREEN_WIDTH + 200
            card.target_y = config.DRAWN_CARD_Y
            if card not in visual_card_list:
                visual_card_list.add(card)

    def draw_card(self, visual_card_list):
        if len(self.draw_pile) > 0:
            card = self.draw_pile.pop()
            card.should_despawn = False 
            return card
        return None
    
    def get_deck_counts(self):
        total = len([c for c in self.master_deck if c.modifier != "destroy"])
        current = len(self.draw_pile) 
        return current, total

class ShopManager:
    def generate_shop(self, shop_list, shop_buttons, current_jokers):
        shop_list.empty()
        shop_buttons.clear()
        
        slots = ['Pack', 'Joker', random.choice(['Pack', 'Joker'])]
        
        owned_keys = [j.key for j in current_jokers]
        available_jokers = [k for k in config.JOKER_DATA.keys() if k not in owned_keys]
        
        start_x = config.SCREEN_WIDTH / 2 - 200
        # Pygame Flip: Bottom half is + instead of -
        pos_y = config.SCREEN_HEIGHT / 2 - 50 
        
        for i, item_type in enumerate(slots):
            pos_x = start_x + (i * 200)
            
            if item_type == 'Pack':
                item = sprites.Pack(config.JOKER_SCALE)
                item.rect.center = (pos_x, pos_y)
                shop_list.add(item)
                btn = ui_elements.TextButton(pos_x, pos_y + 170, 120, 40, f"BUY ${config.PACK_COST}", config.COLOR_PURPLE)
                shop_buttons.append(btn)
                
            elif item_type == 'Joker' and available_jokers:
                key = random.choice(available_jokers)
                available_jokers.remove(key)
                
                item = sprites.Joker(key, config.JOKER_SCALE)
                item._phys_x, item._phys_y = pos_x, pos_y
                item.target_x, item.target_y = pos_x, pos_y
                shop_list.add(item)
                btn = ui_elements.TextButton(pos_x, pos_y + 170, 120, 40, f"BUY ${item.cost}", config.COLOR_BTN_SHOP)
                shop_buttons.append(btn)

    def get_pack_cards(self, master_deck):
        available = [c for c in master_deck if c.modifier != "destroy"]
        num = min(8, len(available))
        return random.sample(available, num)

    def get_pack_modifiers(self):
        keys = list(config.MODIFIER_DATA.keys())
        return random.sample(keys, 2)

class SaveManager:
    def __init__(self):
        self.save_file = "warlatro_save.json"
        self.data = self.load()
        
    def load(self):
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return self.default_save()
        
    def default_save(self):
        return {
            "stats": {
                "highest_level": 1,
                "highest_score": 0,
                "highest_hand_score": 0,
                "hands_played": {}
            },
            "current_game": None
        }
        
    def save(self):
        try:
            with open(self.save_file, "w") as f:
                json.dump(self.data, f)
        except:
            pass
            
    def update_hand_played(self, hand_type):
        self.data["stats"]["hands_played"][hand_type] = self.data["stats"]["hands_played"].get(hand_type, 0) + 1
        self.save()
        
    def update_highest_hand(self, score):
        if score > self.data["stats"]["highest_hand_score"]:
            self.data["stats"]["highest_hand_score"] = score
            self.save()
            
    def update_highest_score(self, score):
        if score > self.data["stats"]["highest_score"]:
            self.data["stats"]["highest_score"] = score
            self.save()
            
    def update_highest_level(self, level):
        if level > self.data["stats"]["highest_level"]:
            self.data["stats"]["highest_level"] = level
            self.save()
            
    def clear_current_game(self):
        self.data["current_game"] = None
        self.save()
        
    def save_current_game(self, game_state_dict):
        self.data["current_game"] = game_state_dict
        self.save()