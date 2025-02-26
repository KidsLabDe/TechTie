import board
import neopixel
import time
import math
import digitalio

# Konfiguration
PIXEL_PIN = board.IO18    # Verwende GPIO18 für das Datensignal
BUTTON_PIN = board.IO17   # Taster an Pin 17
NUM_PIXELS = 6            # 6 NeoPixel LEDs
BRIGHTNESS = 0.3          # Helligkeit (0.0 bis 1.0)
SPEED = 0.05              # Zeit zwischen Animation-Frames (niedrigere Werte = schneller)

# Farbdefinitionen (R, G, B)
BLUE = (0, 50, 255)
ORANGE = (255, 80, 0)
WHITE = (255, 255, 255)
OFF = (0, 0, 0)

# NeoPixel-Objekt initialisieren
pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS, auto_write=False
)

# Taster initialisieren mit Pull-up (Taster gegen GND schalten)
button = digitalio.DigitalInOut(BUTTON_PIN)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP  # Pull-up aktivieren, Taster verbindet mit GND

def wheel(pos):
    """Erzeugt Regenbogenfarben über Position 0-255"""
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)

def blend_colors(color1, color2, blend_amount):
    """Mischt zwei Farben basierend auf dem blend_amount (0.0 bis 1.0)"""
    r = int(color1[0] * (1 - blend_amount) + color2[0] * blend_amount)
    g = int(color1[1] * (1 - blend_amount) + color2[1] * blend_amount)
    b = int(color1[2] * (1 - blend_amount) + color2[2] * blend_amount)
    return (r, g, b)

def fade_value(position, pixel_position, width=2.0):
    """Erzeugt einen Fade-Wert basierend auf der Position"""
    distance = abs(position - pixel_position)
    # Kreisförmige Distanz berücksichtigen (für Übergang am Ende zurück zum Anfang)
    if distance > NUM_PIXELS / 2:
        distance = NUM_PIXELS - distance
    
    # Gaussche Glockenkurve für sanften Fade
    value = math.exp(-(distance * distance) / width)
    return max(0, min(1, value))  # Auf Bereich 0-1 begrenzen

def get_color_for_position(index, pattern_state, color_mode, rainbow_offset=0):
    """Gibt die Farbe für einen bestimmten Index abhängig vom Muster-Status zurück"""
    # Regenbogen-Modus
    if color_mode == 2:
        # Position im Regenbogen basierend auf LED-Index und Offset
        rainbow_pos = (index * 256 // NUM_PIXELS + rainbow_offset) % 256
        return wheel(rainbow_pos)
    
    # Normale Farbmodi
    second_color = WHITE if color_mode == 1 else ORANGE
    
    if pattern_state == 0:  # Muster 1: Blau, Zweite Farbe, Blau, ...
        return BLUE if index % 2 == 0 else second_color
    else:  # Muster 2: Zweite Farbe, Blau, Zweite Farbe, ...
        return second_color if index % 2 == 0 else BLUE

print("NeoPixel Lauflicht mit Taster für Farbwechsel gestartet")
print("Drücke den Taster an Pin 17, um zwischen Blau/Orange, Blau/Weiß und Regenbogen zu wechseln")

try:
    position = 0.0
    pattern_state = 0  # 0 = Blau/Zweite Farbe, 1 = Zweite Farbe/Blau
    color_mode = 0     # 0 = Orange, 1 = Weiß, 2 = Regenbogen
    rainbow_offset = 0 # Offset für Regenbogenfarben
    
    # Entprellen-Variablen
    button_state = False  # Aktueller Zustand
    last_button_state = False  # Vorheriger Zustand
    last_debounce_time = 0  # Zeit des letzten Zustandswechsels
    debounce_delay = 0.05  # Entprellverzögerung in Sekunden
    
    # Zeitpunkt des letzten Muster-Wechsels
    last_pattern_switch = time.monotonic()
    pattern_switch_time = 2  # Zeit in Sekunden bis zum Wechsel des Farbmusters
    
    while True:
        # Taster-Entprellung
        current_time = time.monotonic()
        reading = not button.value  # Invertieren, da Pull-up (False wenn gedrückt)
        
        # Wenn sich der Zustand geändert hat, Zeit zurücksetzen
        if reading != last_button_state:
            last_debounce_time = current_time
        
        # Wenn genug Zeit vergangen ist, um Prellen zu vermeiden
        if current_time - last_debounce_time > debounce_delay:
            # Wenn sich der Zustand seit dem letzten Mal geändert hat
            if reading != button_state:
                button_state = reading
                
                # Wenn der Taster gedrückt wird (LOW wegen Pull-up)
                if button_state:
                    # Wechsle zum nächsten Farbmodus (0->1->2->0)
                    color_mode = (color_mode + 1) % 3
                    if color_mode == 0:
                        mode_name = "Blau/Orange"
                    elif color_mode == 1:
                        mode_name = "Blau/Weiß"
                    else:
                        mode_name = "Regenbogen"
                    print(f"Farbmodus gewechselt: {mode_name}")
        
        # Aktualisiere den vorherigen Zustand
        last_button_state = reading
        
        # Wechsle das Muster periodisch (nur für Nicht-Regenbogen-Modi)
        if color_mode < 2 and current_time - last_pattern_switch > pattern_switch_time:
            pattern_state = 1 - pattern_state  # Wechsle zwischen 0 und 1
            last_pattern_switch = current_time
        
        # Aktualisiere Rainbow-Offset für Animation
        if color_mode == 2:
            rainbow_offset = (rainbow_offset + 5) % 256
        
        # Alle Pixel aktualisieren
        for i in range(NUM_PIXELS):
            if color_mode == 2:
                # Im Regenbogen-Modus: Direkte Farbzuweisung ohne Fade
                pixels[i] = get_color_for_position(i, pattern_state, color_mode, rainbow_offset)
            else:
                # In den anderen Modi: Fade-Effekt anwenden
                intensity = fade_value(position, i)
                base_color = get_color_for_position(i, pattern_state, color_mode)
                pixels[i] = blend_colors(OFF, base_color, intensity)
        
        # Anzeigen
        pixels.show()
        
        # Position weiterbewegen (mit Wrap-Around) - nur für Nicht-Regenbogen-Modi
        if color_mode < 2:
            position = (position + 0.1) % NUM_PIXELS
        
        # Kurze Pause
        time.sleep(SPEED)
            
except KeyboardInterrupt:
    # Bei Tastatur-Unterbrechung alle LEDs ausschalten
    pixels.fill(OFF)
    pixels.show()
    print("Programm beendet")