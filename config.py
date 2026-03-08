import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Constants ---
SCREEN_WIDTH = 1780
SCREEN_HEIGHT = 940
SCREEN_TITLE = "Warlatro: Roguelike War (Pygame Edition)"

CARD_SCALE = 0.8
CARD_WIDTH = 140 * CARD_SCALE
CARD_HEIGHT = 190 * CARD_SCALE

JOKER_SCALE = 0.3
JOKER_WIDTH = 250 * JOKER_SCALE

# Y-Coordinates (Flipped for Pygame: 0 is top, 940 is bottom)
HAND_Y = SCREEN_HEIGHT - 150 
DRAWN_CARD_X = SCREEN_WIDTH / 2
DRAWN_CARD_Y = 480
JOKER_Y = 220 

STIFFNESS = 0.1  
DAMPING = 0.75   

FLOAT_SPEED = 3.0       
FLOAT_RANGE = 3.0       
JOKER_ROT_SPEED = 2.0   
JOKER_ROT_RANGE = 3.0   

MAX_HAND_SIZE = 5
BASE_HANDS_TO_PLAY = 3
MAX_DISCARDS = 4
BASE_TARGET_SCORE = 300
MAX_JOKERS = 5

# --- Colors ---
COLOR_BG = (59, 122, 87)            
COLOR_UI_BG = (26, 36, 33)          
COLOR_BTN_DEFAULT = (128, 128, 128) 
COLOR_BTN_HOVER = (119, 136, 153)   
COLOR_BTN_ACTION = (30, 144, 255)   
COLOR_BTN_SCORE = (255, 165, 0)     
COLOR_BTN_SHOP = (75, 0, 130)       
COLOR_BTN_SELL = (220, 20, 60)      
COLOR_RED = (255, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GREEN = (0, 100, 0)
COLOR_GOLD = (255, 215, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_PURPLE = (128, 0, 128)
COLOR_SHADOW = (0, 0, 0, 100)
COLOR_TOOLTIP_BG = (20, 20, 20, 230) 

# --- Joker Definitions ---
JOKER_DATA = {
    "club_sandwich": {"name": "Club Sandwich", "cost": 6, "desc": "+20 Chips for each Club played", "file": resource_path("assets/jokers/club_sandwich.jpg")},
    "diamond_geezer": {"name": "Diamond Geezer", "cost": 7, "desc": "+4 Mult for each Diamond played", "file": resource_path("assets/jokers/Diamond_Geezer.jpg")},
    "double_trouble": {"name": "Double Trouble", "cost": 7, "desc": "x2 Mult if Two Pair", "file": resource_path("assets/jokers/double_trouble.jpg")},
    "face_value": {"name": "Face Value", "cost": 6, "desc": "+4 Mult for each Face Card played", "file": resource_path("assets/jokers/face_value.jpg")},
    "helping_hand": {"name": "Helping Hand", "cost": 5, "desc": "+1 Hand per Round", "file": resource_path("assets/jokers/helping_hand.jpg")},
    "inflation": {"name": "Inflation", "cost": 6, "desc": "+12 Mult if Hand <= 4 cards", "file": resource_path("assets/jokers/inflation.jpg")},
    "multi_python": {"name": "Multi Python", "cost": 7, "desc": "x2 Mult if 3-card Straight", "file": resource_path("assets/jokers/multi_python.jpg")},
    "national_reserve": {"name": "National Reserve", "cost": 6, "desc": "+10 Chips for each card remaining in deck", "file": resource_path("assets/jokers/national_reserve.jpg")},
    "odd_todd": {"name": "Odd Todd", "cost": 5, "desc": "+30 Chips for Odd card (A,3,5,7,9)", "file": resource_path("assets/jokers/odd_todd.jpg")},
    "pear_up": {"name": "Pear-Up", "cost": 4, "desc": "+8 Mult if Pair", "file": resource_path("assets/jokers/pear_up.jpg")},
    "potato_chip": {"name": "Potato Chip", "cost": 4, "desc": "+50 Chips", "file": resource_path("assets/jokers/potato_chip.jpg")},
    "rainbow_trout": {"name": "Rainbow Trout", "cost": 6, "desc": "x2 Mult if hand contains 4 different suits", "file": resource_path("assets/jokers/rainbow_trout.jpg")},
    "mulligan": {"name": "The Mulligan", "cost": 5, "desc": "+1 Discard per Round", "file": resource_path("assets/jokers/the_muligan.jpg")},
    "the_regular": {"name": "The Regular", "cost": 4, "desc": "+4 Mult", "file": resource_path("assets/jokers/the_regular.jpg")},
    "triple_treat": {"name": "Triple Treat", "cost": 4, "desc": "+12 Mult if 3-of-a-Kind", "file": resource_path("assets/jokers/triple_treat.jpg")},
    "waste_management": {"name": "Waste Management", "cost": 6, "desc": "+1 Mult for every 3 cards discarded this run", "file": resource_path("assets/jokers/Waste_Management.jpg")},
    "wishing_well": {"name": "Wishing Well", "cost": 5, "desc": "Gain $1 for each A, 2, or 3 played", "file": resource_path("assets/jokers/wishing_well.jpg")},
    "severance_package": {"name": "Severance Package", "cost": 5, "desc": "Gain $2 for each Face Card discarded", "file": resource_path("assets/jokers/severance_package.jpg")},
    "the_harvest": {"name": "The Harvest", "cost": 6, "desc": "Gain $5 at the end of the round", "file": resource_path("assets/jokers/the_harvest.jpg")},
    "petty_cash": {"name": "Petty Cash", "cost": 4, "desc": "+3 Chips for every $1 you have", "file": resource_path("assets/jokers/petty_cash.jpg")},
    "capital_gains": {"name": "Capital Gains", "cost": 7, "desc": "x1 Mult for every $10 you have", "file": resource_path("assets/jokers/capital_gains.jpg")}
}

MODIFIER_DATA = {
    "bonus_chips": {"name": "Bonus Card", "desc": "+10 Chips", "color": COLOR_BLUE},
    "mult_plus": {"name": "Mult Card", "desc": "+4 Mult", "color": COLOR_RED},
    "destroy": {"name": "Destroy", "desc": "Remove from Deck", "color": COLOR_BLACK}
}

PACK_COST = 6

# --- AUDIO FILES ---
MUSIC_BG = resource_path("assets/music/background_1.mp3")
MUSIC_STORE = resource_path("assets/music/store_1.mp3")
MUSIC_GAME_OVER = resource_path("assets/music/game_over.mp3")
SOUND_CARD = resource_path("assets/music/card.mp3")
SOUND_PLAY_HAND = resource_path("assets/music/play_hand.mp3")
SOUND_BUY_JOKER = resource_path("assets/music/buy_joker.mp3") 
SOUND_MOD = resource_path("assets/music/mod.mp3")