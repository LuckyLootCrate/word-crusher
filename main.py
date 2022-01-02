import os
import pickle
import pygame as pg
import random
import time

ENTER_CHARACTERS = [pg.K_RETURN, pg.K_KP_ENTER]

WORD_PATH = 'data/words.txt'
PAGES_PATH = 'data/pages'
STATS_PATH = 'data/stats.DAT'
WIDTH = 450
HEIGHT = 600
FOOTER_HEIGHT = 100

SPEED_MULTIPLIER = 0.4
SPAWN_FREQUENCY = 1250 # milliseconds
REVEAL_MULTIPLIER = 2
WORD_SIZE = 50
TEXT_FADE_TIME = 1000
POWERUP_DURATION = 10000

MIN_POWERUP_FREQUENCY = 1000
MAX_POWERUP_FREQUENCY = 30000

# if set to None, powerups are randomised as usual
DEBUG_POWERUP = None


#MIN_POWERUP_FREQUENCY = 1000
#MAX_POWERUP_FREQUENCY = 5000


BASE_LEVEL_UP_THRESHOLD = 10
LEVEL_UP_THRESHOLD_INCREASE = 150
BASE_WORD_DIFFICULTY = 5


# Initialise new stats if they don't exist or load them from existing file
try:
    with open(STATS_PATH, 'rb') as f:
        STATS = pickle.load(f)
        
except FileNotFoundError:
    # Initialise the empty letter counts for destroyed words and letters
    a = {i:0 for i in 'abcdefghijklmnopqrstuvwxyz'}
    b = a.copy()


    STATS = {
        "general": {
            "Games Played": 0,
            "Words Destroyed": 0,
            "Letters Destroyed": 0,
            "Powerups Destroyed": 0,
            
            "Number of Reveals": 0,
            "Letters Missed": 0,

            "Highest Combo": 0,
            "Highest Streak": 0,
            "Highest Score": 0},

        "word": a,
        "letter": b
    }

def save_stats(stats):
    with open(STATS_PATH, 'wb') as f:
        pickle.dump(STATS, f)
    
# How many points you earn from destroying these
WORD_POINTS = 5
LETTER_POINTS = 1

# Points lost from missing
PENALTY_POINTS = 3



SPECIAL_TYPES = {
    "bomb": ["bomb", "boom", "explode", "explosion", "nuke"],
    "clear": ["clear", "wipe", "erase"],
    "score": ["score", "points"],
    "freeze": ["freeze", "stop", "pause"],
    "reveal": ["reveal", "show"],
    "punch": ["punch"],
    "sweep": ["sweep", "multi", "multiple"]
}

common_words = []
difficult_words = []
boss_words = []

icon = pg.image.load('data/icon1.png')
pg.display.set_icon(icon)
pg.init()

# SFX
class SFX:
    SOUNDS = {
        'hit': pg.mixer.Sound('sfx/hit.wav'),
        'destroy': pg.mixer.Sound('sfx/destroy.wav'),
        'reveal': pg.mixer.Sound('sfx/reveal.wav'),
        'miss': pg.mixer.Sound('sfx/miss.wav'),
        'gameover': pg.mixer.Sound('sfx/gameover.wav'),
        'pause': pg.mixer.Sound('sfx/pause.wav'),
        'resume': pg.mixer.Sound('sfx/resume.wav'),
    }

    POWERUP_SOUNDS = {
        'bomb': pg.mixer.Sound('sfx/bomb.wav'),
        'clear': pg.mixer.Sound('sfx/clear.wav'),
        'score': pg.mixer.Sound('sfx/score.wav'),
        'freeze': pg.mixer.Sound('sfx/freeze.wav'),
        'reveal': pg.mixer.Sound('sfx/reveal2.wav'),
        'punch':pg.mixer.Sound('sfx/punch.wav')
    }

    STREAK = []
    COMBO = []

    for file in os.listdir('sfx'):
        path = os.path.join('sfx', file)
        
        if file.startswith('streak'):
            STREAK.append(pg.mixer.Sound(path))

        if file.startswith('combo'):
            COMBO.append(pg.mixer.Sound(path))

    def __init__(self):
        self.muted = False

    def play(self, sound):
        if not self.muted:
            pg.mixer.Sound.play(SFX.SOUNDS[sound])

    def play_powerup_sfx(self, sound):
        if not self.muted:
            pg.mixer.Sound.play(SFX.POWERUP_SOUNDS[sound])

    def play_streak_sfx(self, streak_num):
        if not self.muted:
            pg.mixer.Sound.play(SFX.STREAK[streak_num])

    def play_combo_sfx(self, combo_num):
        if not self.muted:
            pg.mixer.Sound.play(SFX.COMBO[combo_num])

    def mute(self):
        self.muted = True

    def unmute(self):
        self.muted = False


# MUSIC
# Play both songs at the same time, so that the song is filtered in the menu
pg.mixer.pre_init(44100, -16, 2, 2048)
pg.mixer.init()

class Music:
    CHANNELS = {
        "normal": pg.mixer.Channel(0),
        "filter": pg.mixer.Channel(1),
        "menu": pg.mixer.Channel(2)
    }

    SONGS = {
        "Destiny": {
            "normal": pg.mixer.Sound('music/destiny.ogg'),
            "filter": pg.mixer.Sound('music/destiny_filter.ogg'),
            "menu": pg.mixer.Sound('music/destiny_menu.ogg')},
        "Throwback": {
            "normal": pg.mixer.Sound('music/throwback.ogg'),
            "filter": pg.mixer.Sound('music/throwback_filter.ogg'),
            "menu": pg.mixer.Sound('music/throwback_menu.ogg')},
        "Viper": {
            "normal": pg.mixer.Sound('music/viper.ogg'),
            "filter": pg.mixer.Sound('music/viper_filter.ogg'),
            "menu": pg.mixer.Sound('music/viper_menu.ogg')},
        "Waywards": {
            "normal": pg.mixer.Sound('music/waywards.ogg'),
            "filter": pg.mixer.Sound('music/waywards_filter.ogg'),
            "menu": pg.mixer.Sound('music/waywards_menu.ogg')}
    }

    TRACK_LIST = list(SONGS.keys())

    def __init__(self):
        self.state = "menu"
        self.muted = False
        self.song = random.choice(list(Music.SONGS.keys()))

        pos = self.TRACK_LIST.index(self.song)
        self.playlist = self.TRACK_LIST[pos:] + self.TRACK_LIST[:pos]
        
        self.init_song()
        self.play(self.state)

    # Play all songs at once so you can easily switch between them all
    def play(self, state):
        for i, channel in Music.CHANNELS.items():
            if i == state and not self.muted:
                Music.CHANNELS[i].set_volume(1)
                self.state = state
            else:
                Music.CHANNELS[i].set_volume(0)

    def rotate_song(self):
        pos = self.playlist.index(self.song)
        self.song = self.playlist[(pos+1) % len(self.playlist)] 
        self.init_song()
        self.play(self.state)

    def init_song(self):
        for i in Music.CHANNELS:
            Music.CHANNELS[i].play(Music.SONGS[self.song][i], -1)

    def mute(self):
        self.muted = True
        for i in Music.CHANNELS:
            Music.CHANNELS[i].set_volume(0)

    def unmute(self):
        self.muted = False
        for i, channel in Music.CHANNELS.items():
            if i == self.state:
                Music.CHANNELS[i].set_volume(1)

MUSIC = Music()
SOUND = SFX()
            
with open(WORD_PATH, 'r') as f:
    for word in f:
        word = word.rstrip().lower()

        # Do not include words which contain punctuation
        if word.isalpha():
            if len(word) > 9:
                boss_words.append(word)
            elif len(word) > 6:
                difficult_words.append(word)
            elif len(word) > 2:
                common_words.append(word)

screen = pg.display.set_mode((WIDTH, HEIGHT))
caption = pg.display.set_caption("Word Crusher")

#common_words = ['ATTENTION', 'TO', 'ALL', 'MEMBERS', 'OF', 'DERULO', 'DEDICATIONS', 'PLEASE', 'CHANGE', 'YOUR', 'STATUS', 'TO', 'FAN', 'OF', 'Louis', 'Kwan']
#common_words = ["nail", "bail", "rail", "fail", "tail", "pail", "gail", "hail", "jail", "mail", "sail", "wail"]
#common_words = ['ooooo']
#common_words = ['bomb', 'boom', 'chair']
#common_words = ["meme", "bat", "car"]
#common_words = ["bomb", "freeze", "bet"]


class Word:
    
    def __init__(self, value, game):
        self.font = pg.font.SysFont('Times New Roman', game.word_size)
        self.original_value = value.lower()
        self.width, self.height = self.font.size(self.original_value) # dimensions of the rendered word
        self.state = '-' * len(value)
        self.game = game
        
        self.x = random.randint(0, int(WIDTH-self.width)) # this ensures that words don't appear off the screen
        self.y = -self.height
        self.index_target = 0
        self.seed = random.randint(0, 50)

        # if enter is held, ensure that words spawn visible
        if game.visible_words:
            self.reveal()
        
    def __repr__(self):
        return f"Word({self.original_value})"

    def draw(self):
        text = self.font.render(self.state, False, self.color)
        screen.blit(text, (self.x, self.y))

    # 0 will be the fastest and will be black
    # 50 will be the slowest and will be a shade of gray (200, 200, 200)
    @property
    def speed(self):
        return self.game.current_speed_multiplier * ((100 - self.seed) / 100)

    @property
    def color(self):
        if game.redness > 0:
            return ((self.seed*4) + self.game.redness, self.seed*4, self.seed*4)
        return (self.seed*4, self.seed*4, self.seed*4)

    @property
    def is_visible(self):
        return self.game.visible_words

    def move(self):
        self.y += self.speed

    def reveal(self):
        self.state = self.original_value

    def hide(self):
        self.state = '-' * len(self.state)
        self.index_target = 0

    def partially_hide(self):
        word = ''
        for idx, i in enumerate(self.state):
            if i == '*':
                word += self.original_value[idx]
            else:
                word += '-'
        self.state = word

    def partially_reveal(self):
        word = ''
        for idx, i in enumerate(self.state):
            if i == '-':
                word += self.original_value[idx]
            else:
                word += '*'
        self.state = word
            
    @property
    def is_onscreen(self):
        return self.y <= HEIGHT - FOOTER_HEIGHT

    @property
    def is_above_screen(self):
        return self.y < -self.height

    def damage(self, current_letter):
        if self.original_value[self.index_target] == current_letter:
            self.index_target += 1
            self.game.score += round(LETTER_POINTS * self.game.score_multiplier)
            self.game.hit_letter = True

            if self.game.difficulty != 'Difficulty: Gamer':
                STATS['general']["Letters Destroyed"] += 1
                STATS['letter'][current_letter] += 1

            if not self.is_visible:
                word_completed = self.original_value[:self.index_target]
                self.state = word_completed + '-' * (len(self.state) - len(word_completed))
            else:
                word_left = self.original_value[self.index_target:]
                self.state = '*' * (len(self.original_value) - len(word_left)) + word_left
            
            if not self.game.freeze_activated:
                self.y -= self.game.punch * self.speed * 5 * self.game.punch_multiplier # Knock the word slightly upwards after each hit

                if self.game.sweep_activated:
                    for word in self.game.words:
                        word.y -= self.game.punch * word.speed * 5 * self.game.punch_multiplier

        if self.index_target == len(self.original_value):
            self.game.words.remove(self)
            self.game.combo += 1
            self.game.score += round((WORD_POINTS - LETTER_POINTS) * self.game.score_multiplier)
            self.game.destroyed_word = True

            if self.game.difficulty != 'Difficulty: Gamer':
                STATS['general']["Words Destroyed"] += 1
                STATS['word'][self.original_value[0]] += 1

            if isinstance(self, Powerup):
                self.game.powerup = self
                self.game.powerup_footer_text = PowerupFooterText(self, self.game.footer)

                if self.game.difficulty != 'Difficulty: Gamer':
                    STATS['general']["Powerups Destroyed"] += 1
        

class Powerup(Word):
    def __init__(self, special_type, value, game):
        super().__init__(value, game)
        self.type = special_type

    @property
    def color(self):
        return pg.Color('red')

    def __repr__(self):
        return f"Powerup({self.original_value}, {self.type})"

    def activate(self):
        # Destroys random words and grants point bonus for each word destroyed

        calculate_point_increase = False
        
        if self.type == "bomb":
            words = self.game.words.copy()
            random.shuffle(words)
            percentage = round(len(words) * 0.5)
            destroyed = words[:percentage]
            new_score = self.game.score

            for word in words:
                if word in destroyed:
                    self.game.words.remove(word)
                    new_score += int(WORD_POINTS * self.game.score_multiplier * 5)
                    self.game.destroyed_word = True
            calculate_point_increase = True
                    
        if self.type == "clear":
            self.game.words.clear()
            self.game.destroyed_word = True
        
        """
        if self.type == "gamble":
            lucky = random.randint(0, 1)
            if lucky:
                new_score = self.game.score * 2
            else:
                new_score = round(self.game.score / 2)
            calculate_point_increase = True
        """

        if self.type == "score":
            new_score = round(self.game.score * 1.5)
            calculate_point_increase = True

        if self.type == "freeze":
            self.game.toggle_freeze()

        if self.type == "reveal":
            self.game.toggle_reveal()

        if self.type == "punch":
            self.game.toggle_punch()

        if self.type == "sweep":
            self.game.toggle_sweep()

        if calculate_point_increase:
            self.game.point_increase += (new_score - self.game.score)
            self.game.score = new_score

        if self.type not in ["punch", "sweep"]:
            SOUND.play_powerup_sfx(self.type)

        self.game.redness = 35 # changes color of the background
        self.game.powerup = None


class PopUpText:
    """Text which fades away after a certain amount of time."""
    
    def __init__(self, value, x, y, game):
        self.font = pg.font.SysFont('Times New Roman', 20)
        self.value = str(value)
        self.width, self.height = self.font.size(self.value)
        self.alpha = 255
        self.game = game
        self.x = x
        self.y = y

    def draw(self):
        if self.alpha <= 0:
            self.reset()
            
        text = self.font.render(self.value, False, pg.Color('black'))
        text.set_alpha(self.alpha)
        self.alpha -= 255 * 1000 / (self.game.fps * TEXT_FADE_TIME)
        screen.blit(text, (self.x, self.y))

    def reset(self):
        self.alpha = 255

    def set_value(self, value):
        self.value = value


        
class PointIncrease(PopUpText):
    """Just a class which shows numbers pop up from the bottom of the screen so players know how many points they just earnt."""

    def __init__(self, value, game):
        x = 0
        y = HEIGHT - FOOTER_HEIGHT
        super().__init__(value, x, y, game)
        
    def __repr__(self):
        return f"PointIncrease({self.value})"

    def __add__(self, other):
        return PointIncrease(int(float(self.value) + other), self.game)

    def __sub__(self, other):
        return PointIncrease(int(float(self.value) - other), self.game)

    def draw(self):
        """Draw the point increase, where it slowly fades out every frame."""

        value = int(self.value)

        if value > 0:        
            text = self.font.render(f"+{value:,}", False, pg.Color('darkgreen'))
        else:
            text = self.font.render(f"{value:,}", False, pg.Color('red'))

        # Ensures that the point increase text disappears in 3 seconds
        text.set_alpha(self.alpha)
        self.alpha -= 255 * 1000 / (self.game.fps * TEXT_FADE_TIME)
        screen.blit(text, (self.x, self.y - self.height))

        if self.alpha <= 0:
            self.reset()

    def reset(self):
        self.value = '0'
        self.alpha = 255


class LevelUpText(PopUpText):
    def __init__(self, value, game):
        font = pg.font.SysFont('Times New Roman', 20)
        width, height = font.size(value)
        x = WIDTH - width
        y = HEIGHT - FOOTER_HEIGHT - height
        super().__init__(value, x, y, game)


    def draw(self):
        """Draw the point increase, where it slowly fades out every frame."""

        if self.alpha <= 0:
            self.reset()

        # Ensures that the point increase text disappears in 3 seconds
        text = self.font.render(f"{self.value}", False, pg.Color('black'))
        width, height = self.font.size(self.value)
        text.set_alpha(self.alpha)
        self.alpha -= 255 * 1000 / (self.game.fps * TEXT_FADE_TIME)
        screen.blit(text, (WIDTH-width, HEIGHT - FOOTER_HEIGHT - height))

    def reset(self):
        self.value = ''
        self.alpha = 255


class PowerupFooterText:
    def __init__(self, powerup, footer):
        self.font = pg.font.SysFont('Times New Roman', 40)
        self.original_value = powerup.original_value
        self.state = powerup.original_value
        
        self.index_target = 0
        self.game = game
        self.powerup = powerup
        self.footer = footer

    def reset(self):
        self.state = self.original_value
        self.index_target = 0

    def damage(self, current_letter):
        if self.original_value[self.index_target] == current_letter:
            self.index_target += 1
            self.game.hit_letter = True

            word_left = self.original_value[self.index_target:]
            self.state = '*' * (len(self.original_value) - len(word_left)) + word_left
        
        if self.index_target == len(self.original_value):
            self.game.powerup.activate()
            self.game.destroyed_word = True
            self.game.powerup_footer_text = None

    def draw(self):
        powerup = self.font.render(self.state, False, pg.Color('red'))
        powerup_rect = powerup.get_rect(center=self.footer.center)
        screen.blit(powerup, powerup_rect)
   

class Game:
    font = pg.font.SysFont('Times New Roman', 20)

    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.words = []
        self.word_size = WORD_SIZE
        self.running = True
        self.fps = 60
        self.clock = pg.time.Clock()
        self.spawn_frequency = SPAWN_FREQUENCY
        self.base_speed_multiplier = SPEED_MULTIPLIER
        self.current_speed_multiplier = SPEED_MULTIPLIER
        self.spawn_timer = pg.time.get_ticks()
        self.game_over = False
        self.restarting = False
        self.to_menu = False
        
        self.visible_words = False
        
        self.reveal_multiplier = REVEAL_MULTIPLIER * self.base_speed_multiplier # how much the words on the screen speed up by when revealing
        self.reveal_powerup_activated = False
        self.reveal_timer = pg.time.get_ticks()

        self.score = 0
        self.combo = 0
        self.score_based_level = 0

        # For how hard the game should be
        dct = {'Easy': 0, 'Normal': 5, 'Hard': 11, 'Gamer': 100}
        dct = {f"Difficulty: {k}":v for k, v in dct.items()}
        self.background_based_level = dct[self.difficulty]

        # For the score multiplier
        dct = {'Easy': 1, 'Normal': 2, 'Hard': 4, 'Gamer': 1}
        dct = {f"Difficulty: {k}":v for k, v in dct.items()}
        self.score_multiplier = dct[self.difficulty]
        
        self.streak = 0 # how many letters typed in a row without missing or pressing space
        self.streak_text = PopUpText('', WIDTH-100, HEIGHT-(FOOTER_HEIGHT//2)-10, self)
        self.running = True
        self.quitting = False
        self.is_paused = False
        self.word_difficulty = BASE_WORD_DIFFICULTY # this number continually increases
        
        self.level_up_threshold = BASE_LEVEL_UP_THRESHOLD
        self.level_up_text = LevelUpText("", self)
        self.level_up_threshold_multiplier = 1
        self.show_level_up = False
        self.level_up_timer = pg.time.get_ticks()

        self.point_increase = PointIncrease(0, self)
        self.freeze_activated = False
        self.freeze_timer = pg.time.get_ticks()

        self.powerup = None
        self.powerup_footer_text = None
        self.powerup_clock = 0
        self.powerup_frequency = MAX_POWERUP_FREQUENCY
        self.redness = 0

        self.punch_powerup_activated = False
        self.punch_timer = pg.time.get_ticks()
        self.punch_multiplier = 1

        self.sweep_activated = False
        self.sweep_timer = pg.time.get_ticks()

        self.min_powerup_frequency = MIN_POWERUP_FREQUENCY

        if self.difficulty != 'Difficulty: Gamer':
            STATS['general']["Games Played"] += 1
        MUSIC.play("normal")

    @property
    def max_powerup_frequency(self):
        return max(1000, MAX_POWERUP_FREQUENCY - (self.background_based_level * 1000))
    
    @property
    def punch(self):
        return max(0, (self.streak // 10)) + 1
        
    def update_words(self):
        for word in self.words:
            word.draw()
            word.move()

            if word.is_above_screen:
                self.words.remove(word)

    def draw_words(self):
        for word in self.words:
            word.draw()
    
    def reveal_words(self):
        for word in self.words:
            word.reveal()

    def hide_words(self):
        for word in self.words:
            word.hide()

    def partially_hide_words(self):
        for word in self.words:
            word.partially_hide()

    def partially_reveal_words(self):
        for word in self.words:
            word.partially_reveal()

    def toggle_reveal(self):
        self.reveal_timer = pg.time.get_ticks()
        self.reveal_powerup_activated = not self.reveal_powerup_activated
        self.visible_words = not self.visible_words

        # Partially means they reveal and hide words respectively but don't clear word damage
        if self.visible_words:
            self.partially_reveal_words()
        else:
            self.partially_hide_words()

    def toggle_punch(self):
        self.punch_timer = pg.time.get_ticks()
        self.punch_powerup_activated = not self.punch_powerup_activated
        
    def toggle_sweep(self):
        self.sweep_timer = pg.time.get_ticks()
        self.sweep_activated = not self.sweep_activated
        
    def add_streak(self):
        if self.difficulty != 'Difficulty: Gamer':
            STATS['general']["Highest Streak"] = max(STATS['general']["Highest Streak"], self.streak)
        if self.streak >= 10:
            increase = round(self.streak * self.score_multiplier)
            self.score += increase
            self.point_increase += increase
        self.streak = 0

    def add_combo(self):
        if self.difficulty != 'Difficulty: Gamer':
            STATS['general']["Highest Combo"] = max(STATS['general']["Highest Combo"], self.combo)
        if self.combo > 1:
            increase = round(self.combo*75 * self.score_multiplier)
            self.score += increase
            self.point_increase += increase
        self.combo = 0

    def draw_bg(self):
        screen.fill((255, 255-self.redness, 255-self.redness))

        if self.redness > 0:
            self.redness -= (50 * 1000) / (self.fps * POWERUP_DURATION)
        

    def is_special_onscreen(self):
        for word in self.words:
            if type(word) is Powerup and word.is_onscreen:
                return True
        return False

    def update_difficulty(self):
        """
        Difficulty threshold is calculated based on the player's current score, but the difficulty of the game is based on how long the game
        was running for.
        """

        # This is so that the total needed to level up increase a little bit each time
        self.level_up_threshold_multiplier = 1 + (self.score_based_level * 0.1 * self.score_multiplier)
        
        self.level_up_threshold = round(BASE_LEVEL_UP_THRESHOLD + (LEVEL_UP_THRESHOLD_INCREASE * self.score_based_level * self.level_up_threshold_multiplier))

        total_level = self.background_based_level
        self.word_difficulty = BASE_WORD_DIFFICULTY + (total_level)
        self.spawn_frequency = SPAWN_FREQUENCY - (total_level * 25)
        self.base_speed_multiplier = min(SPEED_MULTIPLIER + (0.01*total_level), 0.6)
        self.word_size = max(30, WORD_SIZE - total_level)

    def retry_screen(self):
        self.draw_bg()
        self.draw_words()
        self.draw_footer()
        retry = Game.font.render("Press space to retry!", False, pg.Color('black'))
        retry_rect = retry.get_rect(center=self.footer.center)
        screen.blit(retry, retry_rect)

    def play_streak_sound(self):
        """Start incrementing the streak sound after passing 10 in streak then caps at streak 30."""
        
        if self.streak >= 10 and self.streak % 5 == 0:
            streak_num = (self.streak - 10) // 5

            try:
                SOUND.play_streak_sfx(streak_num)
            except IndexError: # play the last sound if the streak is too high (we want to save the player's ears)
                SOUND.play_streak_sfx(9)

    def play_combo_sound(self):
        """Plays different pitches for the combo sound after from a combo of 2 to 5 max."""

        if self.combo > 1:
            combo_num = self.combo - 2

            try:
                SOUND.play_combo_sfx(combo_num)
            except IndexError:
                SOUND.play_combo_sfx(3)
        
    def check_game_over(self):
        return not all(word.is_onscreen for word in self.words)

    def pause_game(self):
        mask = pg.Surface((WIDTH, HEIGHT))
        screen.fill(pg.Color(pg.Color('black')))
        pause_font = pg.font.SysFont('Times New Roman', 70)
        
        text = pause_font.render("paused", False, pg.Color('white'))
        text_rect = text.get_rect(center=screen.get_rect().center)

        shortcuts = [
            "Press Esc to return to the game",
            "Press R to restart",
            "Press Q to go back to the main menu"
        ]

        y_pos = 375
        subtitle_font = pg.font.SysFont('Times new Roman', 20)
        
        for i in shortcuts:
            subtitle = subtitle_font.render(i, False, pg.Color('white'))
            subtitle_rect = subtitle.get_rect(center=(225, y_pos))
            screen.blit(subtitle, subtitle_rect)
            y_pos += 30
        
        screen.blit(text, text_rect)
        

    def toggle_freeze(self):
        self.freeze_activated = not self.freeze_activated
        self.freeze_timer = pg.time.get_ticks()
        
    def draw_footer(self):
        # Draw the footer with a black border
        pg.draw.rect(screen, pg.Color('black'), pg.Rect(0, HEIGHT-FOOTER_HEIGHT, WIDTH, FOOTER_HEIGHT), 0)
        self.footer = pg.draw.rect(screen, (255, 255-self.redness, 255-self.redness), pg.Rect(0, HEIGHT-FOOTER_HEIGHT+1, WIDTH, FOOTER_HEIGHT), 0)
        
        score = Game.font.render(f"Score: {self.score:,}", False, pg.Color('black'))
        score_rect = score.get_rect(midleft=(10, HEIGHT - (FOOTER_HEIGHT//2)))
        screen.blit(score, score_rect)
        
        if self.streak >= 10:
            self.streak_text.set_value(f"Streak: {self.streak}!")
            self.streak_text.draw()
            self.streak_text.reset()
        else:
            self.streak_text.draw()
            if self.streak_text.alpha <= 0:
                self.streak_text.set_value('')

        if self.powerup_footer_text is not None:
            self.powerup_footer_text.draw()
        
    def update(self, dt):
        if not self.is_paused:
            now = pg.time.get_ticks()
            if self.freeze_activated:
                self.draw_words()
            else:
                self.update_words()

            if self.powerup_footer_text:
                self.powerup_footer_text.draw()
            self.draw_footer()

            if self.punch_powerup_activated:
                self.punch_multiplier = 25
            elif self.sweep_activated:
                self.punch_multiplier = 2
            else:
                self.punch_multiplier = 1

            # Check if score is enough to level up
            if self.score >= self.level_up_threshold:
                self.level_up_text.set_value("Level Up!")
                self.score_based_level += 1

            # Check if score is enough to level down
            elif self.score < BASE_LEVEL_UP_THRESHOLD + (LEVEL_UP_THRESHOLD_INCREASE * (self.score_based_level-1)):
                self.level_up_text.set_value("Level Down!")
                self.score_based_level -= 1

            if self.level_up_text.value != '':
                self.level_up_text.draw()
                    
            self.update_difficulty()


            ### TIMERS ###
            if not self.freeze_activated:
                # Spawn new words at the rate of the spawn frequency
                if now - self.spawn_timer > self.spawn_frequency:
                    self.spawn_timer = now
                    word = self.spawn_common_word()
                    
                # Spawn a special word powerup (this is different to other timers since we don't want it to tick all the time)
                if self.powerup_clock > self.powerup_frequency:
                    self.powerup_clock = 0
                    self.spawn_special_word(DEBUG_POWERUP)
                    self.powerup_frequency = random.randint(self.min_powerup_frequency, self.max_powerup_frequency)

                    print(f"{self.min_powerup_frequency} < {self.powerup_frequency} < {self.max_powerup_frequency}")

                if not self.is_special_onscreen() and self.powerup is None and not self.punch_powerup_activated and not self.sweep_activated:
                    self.powerup_clock += dt
                    
            if now - self.level_up_timer > 30000:
                self.level_up_timer = now
                self.background_based_level += 1
                
            if self.freeze_activated and (now - self.freeze_timer > POWERUP_DURATION or len(self.words) == 0):
                self.freeze_timer = now
                self.toggle_freeze()

            if self.reveal_powerup_activated and now - self.reveal_timer > POWERUP_DURATION:
                self.toggle_reveal()

            if self.punch_powerup_activated and now - self.punch_timer > POWERUP_DURATION:
                self.punch_timer = now
                self.toggle_punch()

            if self.sweep_activated and now - self.sweep_timer > POWERUP_DURATION:
                self.sweep_timer = now
                self.toggle_sweep()
                    
            if int(self.point_increase.value) != 0:
                self.point_increase.draw()

            if self.check_game_over():
                self.game_over = True
                self.reveal_words()
                self.powerup_footer_text = None
                SOUND.play('gameover')
        else:
            self.pause_game()

            
    def event_loop(self):
        keys = pg.key.get_pressed()
        
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.game_over = True
                self.running = False
                self.quitting = True

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.is_paused = not self.is_paused

                    if self.is_paused:
                        SOUND.play('pause')
                        MUSIC.play("filter")
                    else:
                        SOUND.play('resume')
                        MUSIC.play("normal")

                if self.is_paused:
                    if event.unicode.lower() == 'r':
                        self.game_over = True
                        self.restarting = True
                        self.running = False
                        SOUND.play('resume')
                    elif event.unicode.lower() == 'q':
                        self.game_over = True
                        self.restarting = True
                        self.running = False
                        self.quitting = True
                        self.to_menu = True
                        SOUND.play('resume')
                        

                if not self.is_paused:
                    if event.key in ENTER_CHARACTERS and not self.reveal_powerup_activated: # enter key
                        self.reveal_words()
                        self.visible_words = True
                        self.current_speed_multiplier += self.reveal_multiplier
                        SOUND.play('reveal')
                        self.add_streak()

                        if self.difficulty != 'Difficulty: Gamer':
                            STATS['general']["Number of Reveals"] += 1

                        if self.powerup_footer_text:
                            self.powerup_footer_text.reset()
                        
                        
                    # You shouldn't be able to type while the enter key is pressed
                    if event.unicode.isalpha() and not keys[pg.K_RETURN] and not keys[pg.K_KP_ENTER]:
                        current_letter = event.unicode.lower()
                        self.damage_words(current_letter)

            if event.type == pg.KEYUP:
                if event.key in ENTER_CHARACTERS and not self.reveal_powerup_activated:
                    self.current_speed_multiplier = self.base_speed_multiplier
                    self.visible_words = False
                    self.hide_words()
                    

    def await_retry(self):
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    self.running = False
                    SOUND.play('reveal')

                if event.key == pg.K_ESCAPE:
                    self.is_paused = not self.is_paused

                    if self.is_paused:
                        SOUND.play('pause')
                        MUSIC.play("filter")
                    else:
                        SOUND.play('resume')
                        MUSIC.play("normal")

                if self.is_paused:
                    if event.unicode.lower() == 'r':
                        self.game_over = True
                        self.restarting = True
                        self.running = False
                        SOUND.play('resume')
                    elif event.unicode.lower() == 'q':
                        self.game_over = True
                        self.restarting = True
                        self.running = False
                        self.quitting = True
                        self.to_menu = True
                        SOUND.play('resume')

            if event.type == pg.QUIT:
                self.game_over = True
                self.running = False
                self.quitting = True
                
    def spawn_common_word(self):
        x = random.randint(1, self.word_difficulty)

        if x > 20:
            word_list = boss_words
        elif x > 10:
            word_list = difficult_words
        else:
            word_list = common_words
            
        word = Word(random.sample(word_list, 1)[0], self)
        word.draw()
        self.words.append(word)
        return word

    def spawn_special_word(self, special_type=None):
        """Spawn in a random powerup!"""

        if special_type is None:
            special_type = random.choice(list(SPECIAL_TYPES.keys()))

        #word = Powerup('bomb', 'explosion', game)
        word = Powerup(special_type, random.choice(SPECIAL_TYPES[special_type]), game)
        word.draw()
        self.words.append(word)

    def damage_words(self, current_letter):
        self.hit_letter = False
        self.destroyed_word = False

        if self.powerup_footer_text:
            self.powerup_footer_text.damage(current_letter)
            
        for word in self.words.copy():
            word.damage(current_letter)


        # You only want to add 1 to streak for each keystroke, not for each letter hit
        if self.hit_letter:
            self.streak += 1
            if self.punch_powerup_activated or self.sweep_activated:
                SOUND.play_powerup_sfx('punch')
            else:
                SOUND.play('hit')
            self.play_streak_sound()
        else:
            SOUND.play('miss')
            self.point_increase -= round(PENALTY_POINTS * self.score_multiplier)
            self.score = max(0, self.score-PENALTY_POINTS)
            self.add_streak()

            if self.difficulty != 'Difficulty: Gamer':
                STATS['general']["Letters Missed"] += 1

        if self.destroyed_word:
            SOUND.play('destroy')
            self.point_increase += round(WORD_POINTS * self.score_multiplier)

        self.play_combo_sound()
        self.add_combo()

        if self.difficulty != 'Difficulty: Gamer':
            STATS['general']["Highest Score"] = max(STATS['general']["Highest Score"], self.score)


    def run(self):
        dt = self.clock.tick(self.fps)
        self.update(dt)
        self.spawn_common_word()
        
        while self.running:
            while not self.game_over:
                dt = self.clock.tick(self.fps)
                self.event_loop()
                self.draw_bg()
                self.update(dt)
                pg.display.update()

            if not self.restarting:
                self.await_retry()
                self.retry_screen()

                if self.is_paused:
                    self.pause_game()
                
                    
                pg.display.update()
        

class MenuWord:
    
    def __init__(self, value, menu):
        self.font = pg.font.SysFont('Times New Roman', 50)
        self.width, self.height = self.font.size(value) # dimensions of the rendered word
        self.state = value
        self.menu = menu
        
        self.x = random.randint(0, int(WIDTH-self.width)) # this ensures that words don't appear off the screen
        self.y = -self.height + 5
        self.index_target = 0
        self.seed = random.randint(0, 50)
        self.color = (230, 230, 230)
        
    def __repr__(self):
        return f"MenuWord({self.state})"

    def draw(self):
        text = self.font.render(self.state, False, self.color)
        screen.blit(text, (self.x, self.y))

    @property
    def speed(self):
        return SPEED_MULTIPLIER * ((100 - self.seed) / 100) * 5

    def move(self):
        self.y += self.speed
        
    def delete_if_offscreen(self):
        if self.y > HEIGHT:
            self.menu.words.remove(self)

    def damage(self, current_letter):
        if self.state[0] == current_letter:
            self.index_target += 1
            self.menu.hit_letter = True

            self.state = self.state[1:]
            self.y -= 1 # Knock the word slightly upwards after each hit

        if len(self.state) == 0:
            self.menu.words.remove(self)
            self.menu.destroyed_word = True

        
class MainMenu:
    def __init__(self):
        self.running = True
        self.buttons = {}
        self.button_pressed = None
        self.quitting = False

        self.button_width = 200
        self.button_height = 50
        self.words = []

        self.fps = 60
        self.spawn_clock = 0
        self.clock = pg.time.Clock()
        self.spawn_frequency = 1000
        MUSIC.play("menu")

    def draw_bg(self):
        screen.fill((255, 255, 255))

    def draw_title(self):
        font = pg.font.SysFont('Times New Roman', 50)
        text = font.render("Word Crusher", False, pg.Color('black'))
        text_rect = text.get_rect()
        text_rect.center = (WIDTH//2, 140)
        screen.blit(text, text_rect)

    def draw_buttons(self):
        button_x = (WIDTH // 2) - (self.button_width // 2)
        button_y = 210
        button_margin = 25

        for value in ["Play", "Instructions", "Stats", "Quit"]:
            button = Button(button_x, button_y, self.button_width, self.button_height, value)

            is_pressed = button == self.button_pressed
            button.draw(is_pressed)
            button_y += button.height + button_margin
            self.buttons[value] = button

    def draw_cycle_buttons(self):
        margin = 10
        height = 35

        difficulty = ("Difficulty", ["Easy", "Normal", "Hard", "Gamer"], (margin, HEIGHT-height-margin))
        songs = ("Song", MUSIC.playlist, (margin, margin))

        for title, value_list, coords in [difficulty, songs]:
            x, y = coords
            button = CycleButton(x, y, height, title, values=value_list)
            
            is_pressed = self.button_pressed == button
            button.draw(is_pressed)
            self.buttons[title] = button

    def draw_sound_buttons(self):
        width, height = 40, 40
        button_margin = 10

        button_x = WIDTH - button_margin - width
        button_y = button_margin

        for value in ["SFX", "Music"]:
            
            button = ToggleButton(button_x, button_y, width, height, menu, value)
            button.draw()
            button_x -= (width + button_margin)
            self.buttons[value] = button

    def update_words(self):
        for word in self.words:
            word.move()
            word.draw()
            word.delete_if_offscreen()

    def draw_credits(self):
        credit = "Created by LuckyLootCrate#2927"
        font = pg.font.SysFont('Times New Roman', 15)
        
        width, height = font.size(credit)
        name = font.render(credit, 1, pg.Color('black'))
        screen.blit(name, (WIDTH-width, HEIGHT-height))


    def update(self, dt):
        self.spawn_clock += dt
        if self.spawn_clock > self.spawn_frequency:
            self.spawn_word()
            self.spawn_clock -= self.spawn_frequency

        self.update_words()
        self.draw_credits()
        
            
    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()
                
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for button in self.buttons.values():
                    if button.is_mouse_over():
                        self.button_pressed = button
                        SOUND.play('reveal')

                        # If the toggle buttons are activated
                        if button in ToggleButton.STATES:
                            if button.is_activated:
                                if button.value == 'Music':
                                    MUSIC.unmute()
                                    MUSIC.play('menu')
                                elif button.value == 'SFX':
                                    SOUND.unmute()
                                button.toggle()
                            else:
                                if button.value == 'Music':
                                    MUSIC.mute()
                                elif button.value == 'SFX':
                                    SOUND.mute()
                                button.toggle()

                        elif button in CycleButton.STATES:
                            if button.title == "Song":
                                MUSIC.rotate_song()
                            button.rotate_value()
                            break
                        break # Needed so that the sound effect doesn't play a bajillion times
                                

            if event.type == pg.MOUSEBUTTONUP and event.button == 1:
                for button in self.buttons.values():
                    if button.is_mouse_over():
                        if self.button_pressed == button and button not in ToggleButton.STATES and button not in CycleButton.STATES:
                            self.quit()
                            break         
                else:
                    self.button_pressed = None

            if event.type == pg.KEYDOWN:
                if event.unicode.isalpha():
                    current_letter = event.unicode.lower()
                    self.damage_words(current_letter)


    def damage_words(self, current_letter):
        self.hit_letter = False
        self.destroyed_word = False
            
        for word in self.words.copy():
            word.damage(current_letter)

        if self.hit_letter:
            SOUND.play('hit')

        if self.destroyed_word:
            SOUND.play('destroy')

    def spawn_word(self):
        word = MenuWord(random.sample(common_words, 1)[0], self)
        word.draw()
        self.words.append(word)


    def quit(self):
        self.running = False
        self.quitting = True
                
    def run(self):
        while self.running:
            dt = self.clock.tick(self.fps)
            self.draw_bg()
            self.update(dt)
            
            self.draw_title()
            self.draw_buttons()
            self.draw_sound_buttons()
            self.draw_cycle_buttons()
            self.event_loop()
            pg.display.update()


class Button:
    def __init__(self, x, y, width, height, value=''):
        self.font = pg.font.SysFont('Times New Roman', 20)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.value = value
        

    def __repr__(self):
        return f"Button({self.value})"

    def __eq__(self, other):
        return type(self) == type(other) and (self.x, self.y) == (other.x, other.y)

    def __hash__(self):
        return hash((self.x, self.y))

    def draw(self, is_pressed=False):
        roundedness = 10
        pg.draw.rect(screen, pg.Color('black'), (self.x-2, self.y-2, self.width+4, self.height+4), 2, roundedness)

        if is_pressed:
            fill_color = pg.Color('lightgrey')
        else:
            fill_color = pg.Color('white')
            
        pg.draw.rect(screen, fill_color, (self.x, self.y, self.width, self.height), 0, roundedness)

        if self.value != '':
            text = self.font.render(self.value, 1, pg.Color('black'))
            screen.blit(text, (self.x + (self.width/2 - text.get_width()/2), self.y + (self.height/2 - text.get_height()/2)))
            
    def is_mouse_over(self):
        pos = pg.mouse.get_pos()
        if pos[0] > self.x and pos[0] < self.x + self.width:
            if pos[1] > self.y and pos[1] < self.y + self.height:
                return True
        return False


class ToggleButton(Button):
    STATES = {}
    
    def __init__(self, x, y, width, height, menu, value=''):
        super().__init__(x, y, width, height, value)
        self.font = pg.font.SysFont('Times New Roman', 15)

        if self not in self.STATES:
            self.STATES[self] = False
        

    def draw(self):
        roundedness = 10
        pg.draw.rect(screen, pg.Color('black'), (self.x-2, self.y-2, self.width+4, self.height+4), 2, roundedness)

        if self.is_activated:
            fill_color = pg.Color('lightgrey')
        else:
            fill_color = pg.Color('white')
            
        pg.draw.rect(screen, fill_color, (self.x, self.y, self.width, self.height), 0, roundedness)

        if self.value != '':
            text = self.font.render(self.value, 1, pg.Color('black'))
            screen.blit(text, (self.x + (self.width/2 - text.get_width()/2), self.y + (self.height/2 - text.get_height()/2)))

    @property
    def is_activated(self):
        return self.STATES[self]
        
    def toggle(self):
        state = self.STATES[self]
        self.STATES[self] = not state


class CycleButton(Button):
    STATES = {} # Button: index of the state
    
    def __init__(self, x, y, height, title, values):
        """No width is given so that it can be calculated in this __init__ function."""

        self.font = pg.font.SysFont('Times New Roman', 15)
        self.values = values
        self.x = x
        self.y = y
        self.title = title

        # Get the index stored from STATES if the button exists
        # If not, get the first element as default
        for button in self.STATES:
            if button.values == self.values:
                self.value = self.values[self.STATES[button]]
                break
        else:
            self.value = self.values[0]
            self.STATES[self] = 0

        self.value = f"{self.title}: {self.value}"
        width = self.font.size(self.value)[0]
        margin = 10
        super().__init__(x, y, width+(margin*5), height, self.value)
        

    def rotate_value(self): 
        val = self.STATES[self]
        self.STATES[self] = (val+1) % len(self.values)

    
class PageTemplate:
    def __init__(self):
        self.page_number = 1
        self.running = True
        self.quitting = False

        self.button_width = 100
        self.button_height = 50
        self.button_pressed = ''
        self.button_values = ['Previous', 'Menu', 'Next']

    def draw_bg(self):
        screen.fill(pg.Color('white'))

    def draw_buttons(self):
        margin_x = 25
        button_y = HEIGHT - 100
        self.buttons = {}
        
        if self.page_number > 1:
            self.buttons['Previous'] = Button(margin_x, button_y, self.button_width, self.button_height, "Previous")
        if self.page_number < len(self.pages):
            self.buttons['Next'] = Button(WIDTH-margin_x-self.button_width, button_y, self.button_width, self.button_height, "Next")

        self.buttons['Menu'] = Button((WIDTH//2) - (self.button_width//2), button_y, self.button_width, self.button_height, "Menu")


        for value in self.button_values:
            if value in self.buttons:
                button = self.buttons[value]
                is_pressed = value == self.button_pressed
                button.draw(is_pressed)
                

    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()
                
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for value in self.buttons:
                    if self.buttons[value].is_mouse_over():
                        self.button_pressed = value
                        SOUND.play('reveal')

            if event.type == pg.MOUSEBUTTONUP and event.button == 1:
                for value in self.buttons:
                    if self.buttons[value].is_mouse_over() and self.button_pressed == value:
                        if value == 'Previous':
                            self.page_number -= 1
                        elif value == 'Next':
                            self.page_number += 1
                        elif value == 'Menu':
                            self.running = False
                
                self.button_pressed = ''
            
    def run(self):
        while self.running:
            self.event_loop()
            self.draw_bg()
            self.draw_buttons()
            pg.display.update()

    def quit(self):
        self.running = False
        self.quitting = True


class Page:
    def __init__(self, path, is_image, title, lines):
        self.path = path
        self.is_image = is_image
        self.title = title
        self.lines = lines
        self.line_font = pg.font.SysFont('Times new Roman', 20)
        self.line_y_pos = 90
        
    @classmethod
    def load_from_img(cls, path):
        """For loading the instructions."""
        return cls(path=path, is_image=True, title=None, lines=None)

    @classmethod
    def load(cls, title, lines):
        """For loading the stats. Lines should be an array, containing a sentence as the element."""
        return cls(path=None, is_image=False, title=title, lines=lines)

    def draw(self, style=''):
        """Style should be either 'list' or 'grid'."""
        
        if self.is_image:
            page = pg.image.load(self.path)
            screen.blit(page, (0, 0))
        else:
            font_size = 40
            font = pg.font.SysFont("Times New Roman", font_size)

            # Keep shrinking title until it fits on screen
            while font.size(self.title)[0] > WIDTH:
                font_size -= 5
                font = pg.font.SysFont("Times New Roman", font_size)

            # Put title in the middle of the screen
            title = font.render(self.title, False, pg.Color('black'))
            width, height = font.size(self.title)
            screen.blit(title, ((WIDTH//2) - (width//2), 30))
            
            if style.lower() == 'list':
                self.draw_list_layout()
            else:
                self.draw_grid_layout()


    def draw_list_layout(self):
        y_pos = 125
        
        for line in self.lines:
            width = self.line_font.size(line)[0]
            line = self.line_font.render(line, False, pg.Color('black'))
            line_rect = line.get_rect(center=(WIDTH//2, y_pos))
            screen.blit(line, line_rect)
            y_pos += 35
            
        
    def draw_grid_layout(self):
        """Creates a 2 by x grid pattern."""

        mid = len(self.lines) // 2
        left, right = self.lines[:mid], self.lines[mid:]

        longest_width = max([self.line_font.size(i)[0] for i in self.lines])
        margin = round((WIDTH - (longest_width*2)) / 3)
        x_pos = margin

        for column in [left, right]:
            y_pos = self.line_y_pos

            for row in column:
                text = self.line_font.render(row, False, pg.Color('black'))
                screen.blit(text, (x_pos, y_pos))
                y_pos += 30

            x_pos = WIDTH - margin - longest_width
    
class Instructions(PageTemplate):
    def __init__(self, pages):
        super().__init__()
        self.pages = pages
        

    def draw_bg(self):
        screen.fill(pg.Color('white'))
        bg = self.pages[self.page_number - 1]
        bg.draw()

    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()
                
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for value in self.buttons:
                    if self.buttons[value].is_mouse_over():
                        self.button_pressed = value
                        SOUND.play('reveal')

            if event.type == pg.MOUSEBUTTONUP and event.button == 1:
                for value in self.buttons:
                    if self.buttons[value].is_mouse_over() and self.button_pressed == value:
                        if value == 'Previous':
                            self.page_number -= 1
                        elif value == 'Next':
                            self.page_number += 1
                            if self.page_number == 21:
                                MUSIC.mute()
                                time.sleep(1.5)
                                self.quit()
                        elif value == 'Menu':
                            self.running = False
                
                self.button_pressed = ''


class Stats(PageTemplate):
    def __init__(self):
        super().__init__()
        self.pages = self.generate_pages()

    def draw_bg(self):
        screen.fill(pg.Color('white'))
        bg = self.pages[self.page_number - 1]

        style = 'list' if self.page_number == 1 else 'grid'
        bg.draw(style)

    @staticmethod
    def generate_stat_page():
        title = "Overall Statistics"
        lines = []
        general_dct = STATS['general']
    
        for k, v in general_dct.items():
            lines.append(f"{k}: {v:,}")

        # Calculating Accuracy
        hit, miss = general_dct["Letters Destroyed"], general_dct["Letters Missed"]
        total = hit + miss

        try:
            accuracy = f"{hit/total:.0%}"
        except ZeroDivisionError:
            accuracy = "NaN"
            
        lines.append(f"Accuracy: {accuracy}")
        return Page.load(title, lines)
        
    @staticmethod
    def generate_word_page():
        title = "Destroyed Words Which..."
        lines = []
        word_dct = STATS['word']

        # Sort by most destroyed word first
        for k in word_dct:
            lines.append(f"...Start with {k.upper()}: {word_dct[k]:,}")
        return Page.load(title, lines)

    @staticmethod
    def generate_letter_page():
        title = "Destroyed Letters"
        lines = []
        letter_dct = STATS['letter']

        # Sort by most destroyed letter first
        for k in letter_dct:
            lines.append(f"{k.upper()}: {letter_dct[k]:,}")
        return Page.load(title, lines)

    def generate_pages(self):
        return [
            self.generate_stat_page(),
            self.generate_word_page(),
            self.generate_letter_page()
        ]
            

if __name__ == "__main__":

    # Load instruction pages
    pages = []
    for idx, file in enumerate(os.listdir(PAGES_PATH)):
        path = os.path.join(PAGES_PATH, file)
        page = Page.load_from_img(path)
        pages.append(page)
    
    while True:
        first_run = True
        save_stats(STATS)
        menu = MainMenu()
        menu.run()

        if menu.button_pressed == menu.buttons['Play']:
            while first_run or not game.quitting:
                first_run = False
                
                difficulty = menu.buttons['Difficulty'].value
                
                game = Game(difficulty)
                game.run()

            if not game.to_menu:
                break

        elif menu.button_pressed == menu.buttons['Instructions']:
            
            instructions = Instructions(pages)
            instructions.run()

            if instructions.quitting:
                break

        elif menu.button_pressed == menu.buttons['Stats']:
            stats = Stats()
            stats.run()

            if stats.quitting:
                break

        else:
            break

    save_stats(STATS)
    pg.quit()
