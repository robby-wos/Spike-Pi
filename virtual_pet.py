#test    
#test    

import pygame
import os
import random
import time
import json
from datetime import datetime, timedelta

pygame.init()
pygame.mixer.init()

# Pi-friendly display setup
import os
os.environ['SDL_VIDEODRIVER'] = 'fbcon'  # Use framebuffer
os.environ['SDL_FBDEV'] = '/dev/fb0'

print("Initializing display...")
# Try fullscreen first, fallback to windowed if needed
try:
    screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
    print("Fullscreen mode successful")
except:
    print("Fullscreen failed, using 800x600 window")
    screen = pygame.display.set_mode((800, 600))

print(f"Screen size: {screen.get_size()}")
pygame.display.set_caption("Spike the SDR")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24, bold=True)  # Increased size from 14 to 24, added bold=True

# Constants
DECAY_TO_ZERO_SECONDS = 3 * 24 * 60 * 60  # 3 days
FRAMES_PER_SECOND = 30
HUNGER_DECAY_PER_FRAME = 100 / (DECAY_TO_ZERO_SECONDS * FRAMES_PER_SECOND)

def load_animation_frames(folder_path):
    frames = []
    try:
        if not os.path.exists(folder_path):
            print(f"Warning: Folder {folder_path} does not exist!")
            return frames
            
        files = [f for f in sorted(os.listdir(folder_path)) if f.endswith(".png")]
        for f in files:
            file_path = os.path.join(folder_path, f)
            try:
                # Check if file is actually an image
                with open(file_path, 'rb') as img_file:
                    header = img_file.read(8)
                    if not header.startswith(b'\x89PNG\r\n\x1a\n'):
                        print(f"Warning: {file_path} is not a valid PNG file (possibly LFS pointer)")
                        continue
                        
                frame = pygame.image.load(file_path).convert_alpha()
                frames.append(frame)
                print(f"Successfully loaded: {file_path}")
            except pygame.error as e:
                print(f"Error loading {file_path}: {e}")
            except Exception as e:
                print(f"Unexpected error loading {file_path}: {e}")
    except Exception as e:
        print(f"Error accessing folder {folder_path}: {e}")
    
    return frames

# Load animations with fallbacks
background_frames = load_animation_frames("background_frames")
if not background_frames:
    # Create a simple blue background as fallback
    fallback_bg = pygame.Surface((800, 600))
    fallback_bg.fill((50, 100, 150))
    background_frames = [fallback_bg]
print("Loaded backgrounds:", len(background_frames))

idle_frames = load_animation_frames("pet_idle_frames")
if not idle_frames:
    # Create simple colored squares as fallback pet
    for i in range(4):
        fallback_pet = pygame.Surface((200, 200))
        color_intensity = 100 + (i * 30)
        fallback_pet.fill((0, color_intensity, 0))
        idle_frames.append(fallback_pet)
print("Loaded idle frames:", len(idle_frames))

feed_frames = load_animation_frames("pet_feed_frames")
if not feed_frames:
    feed_frames = idle_frames.copy()  # Use idle frames as fallback
print("Loaded feed frames:", len(feed_frames))

sleeping_frames = load_animation_frames("pet_sleeping_frames")
if not sleeping_frames:
    sleeping_frames = idle_frames.copy()
print("Loaded sleeping frames:", len(sleeping_frames))

falling_asleep_frames = load_animation_frames("pet_falling_asleep_frames")
if not falling_asleep_frames:
    falling_asleep_frames = idle_frames.copy()
print("Loaded falling asleep frames:", len(falling_asleep_frames))

# Load sounds with error handling
try:
    feed_sound = pygame.mixer.Sound("sounds/feed.wav")
    sleep_sound = pygame.mixer.Sound("sounds/sleep.wav")
    wake_sound = pygame.mixer.Sound("sounds/wake.wav")
    mail_sound = pygame.mixer.Sound("sounds/mail.wav")
    print("All sounds loaded successfully")
except Exception as e:
    print(f"Error loading sounds: {e}")
    # Create silent sounds as fallback
    feed_sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
    sleep_sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
    wake_sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
    mail_sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)

# Save/Load functions
def save_game_data():
    data = {
        'meetings_booked': meetings_booked,
        'last_meeting_date': last_meeting_date.isoformat(),
        'tips_sent_today': tips_sent_today,
        'today_date': today_date.isoformat()
    }
    try:
        with open('pet_save.json', 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving game data: {e}")

def load_game_data():
    try:
        with open('pet_save.json', 'r') as f:
            data = json.load(f)
            return (
                data.get('meetings_booked', 0),
                datetime.fromisoformat(data.get('last_meeting_date', datetime.now().date().isoformat())).date(),
                data.get('tips_sent_today', 0),
                datetime.fromisoformat(data.get('today_date', datetime.now().date().isoformat())).date()
            )
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"No save file found or error loading: {e}")
        return 0, datetime.now().date(), 0, datetime.now().date()

# Load saved data
meetings_booked, last_meeting_date, tips_sent_today, today_date = load_game_data()

# States
health = 100
hunger = 100
# meetings_booked, last_meeting_date, tips_sent_today, today_date now loaded from save file
feed_cooldown = 5
last_feed_time = 0

status_modes = ["Cold Calling", "Prospecting", "Reporting", "Beasting", "Crying", "Getting Yelled At"]
status_index = 0
last_status_change = time.time()
status_change_interval = 1800  # 30 minutes

# Tips
tips = [
    "COFFEES FOR CLOSERS",
    "Worst thing, you get an extra dollar.",
    "Help me",
    "Jack... nevermind",
    "Smile and dial",
    "Thank you for keeping me alive",
    "I <3 Echo Bunny Man",
    "Mr. Brightside",
    "GET BACK TO WORK SOLDIER",
    "Send another email, that'll help",
    "1 calendar invite and a dream",
    "Hang up on them instead",
    "Lets get that chedda",
    "Dont celebrate in the parking lot",
    "CAH A CAR AND A DEEA",
    "ABT",
    "Once you get the yes get out",
    "Never wear your bag on your right arm",
    "Pete Knows Best",
    "NO SNEAKERS",
    "ECHO BRAVO MIKE",
    "JIMMY... watch that jargon mouth.",
    "Permission based email"
]
speech_override = None
speech_timer = 0
speech_duration = 3000
# tips_sent_today now loaded from save file
max_daily_tips = random.randint(2, 3)
daily_tip_times = []
mail_flag = False

# Combo tracking
combo_counter = 0
last_combo_time = 0
combo_timeout = 5

# Animation frame trackers
current_frame = 0
frame_direction = 1
bg_frame_index = 0
bg_frame_timer = 0
bg_frame_delay = 5

# Action states
action_state = None  # 'feeding', 'sleeping', 'falling_asleep'
action_start_time = 0
action_duration = {
    "feeding": 5000,
    "falling_asleep": 1000,
    "sleeping": 5000
}

print("Starting main game loop...")
frame_count = 0
running = True
while running:
    frame_count += 1
    if frame_count % 30 == 0:  # Print every 30 frames (1 second)
        print(f"Frame {frame_count}, FPS: {clock.get_fps():.1f}")
    
    now = datetime.now()
    screen_width, screen_height = screen.get_size()
    
    # Clear screen to white first (so we know if anything is rendering)
    screen.fill((255, 255, 255))
    
    if frame_count < 10:  # Debug first few frames
        print(f"Frame {frame_count}: screen size {screen_width}x{screen_height}")
        
    ui_box_width = int(screen_width * 0.22)
    ui_box_height = int(screen_height * 0.15)
    ui_box_x = int(screen_width * 0.015)
    ui_box_y = int(screen_height * 0.025)

    health_bar_width = int(ui_box_width * 0.55)
    health_bar_height = int(ui_box_height * 0.18)
    health_bar_x = ui_box_x + int(ui_box_width * 0.09)
    health_bar_y = ui_box_y + int(ui_box_height * 0.18)

    hunger_bar_width = health_bar_width
    hunger_bar_height = health_bar_height
    hunger_bar_x = health_bar_x
    hunger_bar_y = health_bar_y + int(ui_box_height * 0.22)

    health_text_x = health_bar_x + health_bar_width + int(ui_box_width * 0.06)
    health_text_y = health_bar_y
    hunger_text_x = hunger_bar_x + hunger_bar_width + int(ui_box_width * 0.06)
    hunger_text_y = hunger_bar_y

    mood_text_x = health_bar_x
    mood_text_y = ui_box_y + int(ui_box_height * 0.75)    
    pet_width, pet_height = screen_width // 2, screen_height // 2
    pet_center = (screen_width // 2, screen_height // 2)
    
    # Daily reset
    if now.date() != today_date:
        today_date = now.date()
        if today_date.weekday() <= 3:
            # Don't reset meetings_booked - keep it persistent!
            tips_sent_today = 0
            max_daily_tips = random.randint(2, 3)
            daily_tip_times = sorted([
                datetime.combine(today_date, datetime.strptime(f"{random.randint(8, 14)}:{random.randint(30, 59)}", "%H:%M").time())
                for _ in range(max_daily_tips)
            ])
        save_game_data()  # Save when date changes

    current_time_str = now.strftime("%H:%M")

    # Auto wake
    if current_time_str == "08:30" and action_state == "sleeping":
        wake_sound.play()
        action_state = None
        speech_override = "Time to rise and book some meetings!"
        speech_timer = pygame.time.get_ticks()

    # Auto sleep
    if current_time_str == "15:45" and action_state not in ["sleeping", "falling_asleep"]:
        sleep_sound.play()
        action_state = "falling_asleep"
        action_start_time = pygame.time.get_ticks()

    # Status update every 30 min
    if today_date.weekday() <= 3 and time.time() - last_status_change >= status_change_interval:
        status_index = (status_index + 1) % len(status_modes)
        last_status_change = time.time()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:  # Press ESC to quit
                running = False
            if event.key == pygame.K_f and time.time() - last_feed_time > feed_cooldown:
                feed_sound.play()
                last_feed_time = time.time()
                meetings_booked += 1
                last_meeting_date = today_date
                save_game_data()  # Save immediately when meeting is booked
                if time.time() - last_combo_time < combo_timeout:
                    combo_counter += 1
                else:
                    combo_counter = 1
                last_combo_time = time.time()
                action_state = "feeding"
                action_start_time = pygame.time.get_ticks()
            elif event.key == pygame.K_s:
                if action_state != "sleeping":
                    sleep_sound.play()
                    action_state = "falling_asleep"
                    action_start_time = pygame.time.get_ticks()
            elif event.key == pygame.K_z:
                sleep_sound.play()
                action_state = "sleeping"
                action_start_time = pygame.time.get_ticks()
            elif event.key == pygame.K_w:
                wake_sound.play()
                action_state = None
            elif event.key == pygame.K_t:
                speech_override = random.choice(tips)
                speech_timer = pygame.time.get_ticks()
                mail_flag = False

    # Speech timeout
    if speech_override and pygame.time.get_ticks() - speech_timer > speech_duration:
        speech_override = None

    # Deliver tips if scheduled
    if today_date.weekday() <= 3:
        if tips_sent_today < max_daily_tips and len(daily_tip_times) > tips_sent_today:
            if now >= daily_tip_times[tips_sent_today] and action_state not in ["sleeping", "falling_asleep"]:
                try:
                    mail_sound.play()
                except:
                    pass  # Ignore sound errors
                speech_override = random.choice(tips)
                speech_timer = pygame.time.get_ticks()
                mail_flag = True
                tips_sent_today += 1

    # Draw background
    try:
        if background_frames and len(background_frames) > 0:
            bg_surface = pygame.transform.scale(background_frames[bg_frame_index], (screen_width, screen_height))
            screen.blit(bg_surface, (0, 0))
        else:
            # Fallback background - gradient blue
            for y in range(screen_height):
                color_val = int(50 + (y / screen_height) * 100)
                pygame.draw.line(screen, (color_val, color_val, 255), (0, y), (screen_width, y))
    except Exception as e:
        print(f"Background draw error: {e}")
        screen.fill((100, 150, 200))  # Simple blue background
    
    # Handle action animations
    if action_state == "feeding":
        elapsed = pygame.time.get_ticks() - action_start_time
        if feed_frames:
            frame_index = int((elapsed / action_duration["feeding"]) * len(feed_frames))
            if 0 <= frame_index < len(feed_frames):
                feed_frame_scaled = pygame.transform.scale(feed_frames[frame_index], (pet_width, pet_height))
                feed_rect = feed_frame_scaled.get_rect(center=pet_center)
                screen.blit(feed_frame_scaled, feed_rect)
                print("Feeding frame:", frame_index)
            else:
                hunger = min(100, hunger + 10)
                action_state = None
                mail_flag = True
        else:
            pygame.draw.rect(screen, (255,0,0), (pet_center[0]-100, pet_center[1]-100, 200, 200))
            print("Feed frames missing!")

    elif action_state == "falling_asleep":
        elapsed = pygame.time.get_ticks() - action_start_time
        if falling_asleep_frames:
            frame_index = int((elapsed / action_duration["falling_asleep"]) * len(falling_asleep_frames))
            if 0 <= frame_index < len(falling_asleep_frames):
                fa_frame_scaled = pygame.transform.scale(falling_asleep_frames[frame_index], (pet_width, pet_height))
                fa_rect = fa_frame_scaled.get_rect(center=pet_center)
                screen.blit(fa_frame_scaled, fa_rect)
                print("Falling asleep frame:", frame_index)
            else:
                action_state = "sleeping"
                action_start_time = pygame.time.get_ticks()
        else:
            pygame.draw.rect(screen, (0,0,255), (pet_center[0]-100, pet_center[1]-100, 200, 200))
            print("Falling asleep frames missing!")

    elif action_state == "sleeping":
        elapsed = pygame.time.get_ticks() - action_start_time
        if sleeping_frames:
            frame_index = int((elapsed / 300) % len(sleeping_frames))
            sleep_frame_scaled = pygame.transform.scale(sleeping_frames[frame_index], (pet_width, pet_height))
            sleep_rect = sleep_frame_scaled.get_rect(center=pet_center)
            screen.blit(sleep_frame_scaled, sleep_rect)
            print("Sleeping frame:", frame_index)
        else:
            pygame.draw.rect(screen, (128,128,128), (pet_center[0]-100, pet_center[1]-100, 200, 200))
            print("Sleeping frames missing!")

    else:
        # Idle pet animation
        if idle_frames:
            current_frame += frame_direction
            if current_frame >= len(idle_frames) - 1 or current_frame <= 0:
                frame_direction *= -1
            bg_frame_timer += 1
            if bg_frame_timer >= bg_frame_delay:
                bg_frame_index = (bg_frame_index + 1) % len(background_frames)
                bg_frame_timer = 0

            if 0 <= current_frame < len(idle_frames):
                frame_scaled = pygame.transform.scale(idle_frames[current_frame], (pet_width, pet_height))
                pet_rect = frame_scaled.get_rect(center=pet_center)
                screen.blit(frame_scaled, pet_rect)
                print("Idle frame:", current_frame)
        else:
            pygame.draw.rect(screen, (0,255,0), (pet_center[0]-100, pet_center[1]-100, 200, 200))
            print("Idle frames missing!")

        # Hunger decay (only while idle on weekdays)
        if today_date.weekday() <= 3:
            hunger = max(0, hunger - HUNGER_DECAY_PER_FRAME)

    # HUD Elements (scaled and responsive)
    pygame.draw.rect(screen, (0, 0, 0), (ui_box_x, ui_box_y, ui_box_width, ui_box_height), border_radius=8)
    pygame.draw.rect(screen, (255, 255, 255), (ui_box_x, ui_box_y, ui_box_width, ui_box_height), 2, border_radius=8)

    pygame.draw.rect(screen, (255, 0, 0), (health_bar_x, health_bar_y, health_bar_width, health_bar_height))  # Health bar bg
    pygame.draw.rect(screen, (0, 255, 0), (health_bar_x, health_bar_y, int(health_bar_width * health / 100), health_bar_height))  # Health value

    pygame.draw.rect(screen, (50, 50, 50), (hunger_bar_x, hunger_bar_y, hunger_bar_width, hunger_bar_height))  # Hunger bar bg
    pygame.draw.rect(screen, (255, 165, 0), (hunger_bar_x, hunger_bar_y, int(hunger_bar_width * hunger / 100), hunger_bar_height))  # Hunger value

    screen.blit(font.render("Health", True, (255, 255, 255)), (health_text_x, health_text_y))
    screen.blit(font.render("Hunger", True, (255, 255, 255)), (hunger_text_x, hunger_text_y))

    mood = "Dominating" if hunger > 80 else "Chill" if hunger > 50 else "Meh" if hunger > 30 else "Send help"
    screen.blit(font.render(f"Mood: {mood}", True, (255, 255, 255)), (mood_text_x, mood_text_y))

    # Meetings and Status (top right example positions)
    meetings_text_x = int(screen_width * 0.75)
    meetings_text_y = int(screen_height * 0.06)
    status_text_x = meetings_text_x
    status_text_y = meetings_text_y + int(ui_box_height * 0.25)
    combo_text_x = meetings_text_x
    combo_text_y = status_text_y + int(ui_box_height * 0.22)
    mail_text_x = ui_box_x + ui_box_width // 2
    mail_text_y = ui_box_y - int(ui_box_height * 0.4)

    screen.blit(font.render(f"Meetings: {meetings_booked}", True, (255, 255, 255)), (meetings_text_x, meetings_text_y))
    screen.blit(font.render(f"Status: {status_modes[status_index]}", True, (255, 255, 255)), (status_text_x, status_text_y))

    if combo_counter > 1:
        screen.blit(font.render(f"Combo x{combo_counter}!", True, (255, 200, 0)), (combo_text_x, combo_text_y))

    if mail_flag:
        screen.blit(font.render("New Tip!", True, (255, 255, 0)), (mail_text_x, mail_text_y))

    # Time (bottom right)
    now_time = datetime.now().strftime("%H:%M:%S")
    time_text_x = int(screen_width * 0.85)
    time_text_y = int(screen_height * 0.93)
    screen.blit(font.render(now_time, True, (255, 255, 255)), (time_text_x, time_text_y))

    # Speech bubble (centered horizontally, scaled vertically)
    if speech_override:
        text = font.render(speech_override, True, (20, 20, 20))
        bubble = pygame.Surface((text.get_width() + 20, 40), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (235, 230, 210, 240), bubble.get_rect(), border_radius=6)
        pygame.draw.rect(bubble, (70, 40, 20), bubble.get_rect(), 2, border_radius=6)
        bubble.blit(text, (10, 10))
        bubble_x = screen_width // 2 - bubble.get_width() // 2
        bubble_y = int(screen_height * 0.25)
        screen.blit(bubble, (bubble_x, bubble_y))

    # Force a simple test draw to ensure screen is working
    if frame_count < 60:  # First 2 seconds
        test_color = (255, 0, 0) if frame_count % 60 < 30 else (0, 255, 0)
        pygame.draw.circle(screen, test_color, (100, 100), 50)
        pygame.draw.rect(screen, (255, 255, 0), (200, 50, 100, 100))
        test_text = font.render(f"Frame {frame_count}", True, (0, 0, 0))
        screen.blit(test_text, (50, 200))

    pygame.display.flip()  # Use flip() instead of update() for better performance
    clock.tick(FRAMES_PER_SECOND)

# Save data one final time before quitting
save_game_data()
pygame.quit()