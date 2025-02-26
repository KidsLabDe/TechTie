import time
import board
import neopixel
import digitalio
import wifi
import math

# Konfiguration
PIXEL_PIN = board.IO18    # NeoPixel-Datenpin
BUTTON_PIN = board.IO17   # Taster-Pin
NUM_PIXELS = 6            # Anzahl der NeoPixels
BRIGHTNESS = 0.3          # Helligkeit der LEDs
SCAN_INTERVAL = 5         # Sekunden zwischen WLAN-Scans

# Farbdefinitionen für verschiedene Signalstärken
# Farben gehen von Rot (schwaches Signal) über Gelb zu Grün (starkes Signal)
SIGNAL_COLORS = [
    (255, 0, 0),      # Sehr schwach: Rot
    (255, 60, 0),     # Schwach: Orange-Rot
    (255, 120, 0),    # Mäßig: Orange
    (255, 200, 0),    # Gut: Gelb-Orange
    (150, 255, 0),    # Sehr gut: Gelb-Grün
    (0, 255, 0)       # Ausgezeichnet: Grün
]

# Signalstärke-Schwellwerte in dBm (typische WLAN-Werte)
# -30 dBm ist ausgezeichnet, -90 dBm ist sehr schwach
SIGNAL_THRESHOLDS = [-90, -80, -70, -60, -50, -40]

# NeoPixel initialisieren
pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS, auto_write=False
)

# Taster initialisieren (optional für Moduswechsel)
button = digitalio.DigitalInOut(BUTTON_PIN)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# LED für Statusanzeige
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

def map_signal_to_color(signal_strength):
    """Wandelt Signalstärke (dBm) in eine Farbe um"""
    for i, threshold in enumerate(SIGNAL_THRESHOLDS):
        if signal_strength <= threshold:
            return SIGNAL_COLORS[i]
    return SIGNAL_COLORS[-1]  # Bestes Signal

def get_signal_index(signal_strength):
    """Gibt den Signalstärke-Index (0-5) basierend auf dBm zurück"""
    for i, threshold in enumerate(SIGNAL_THRESHOLDS):
        if signal_strength <= threshold:
            return i
    return 5  # Bestes Signal

def scan_wifi():
    """Scannt nach WLAN-Netzwerken und gibt sie sortiert nach Signalstärke zurück"""
    print("Scanne nach WLAN-Netzwerken...")
    networks = []
    
    try:
        # LED einschalten während des Scans
        led.value = True
        
        # Starte den Scan
        for network in wifi.radio.start_scanning_networks():
            # Sammle Netzwerkinformationen
            networks.append({
                'ssid': network.ssid,
                'rssi': network.rssi,
                'channel': network.channel
            })
        
        # Stoppe den Scan
        wifi.radio.stop_scanning_networks()
        
        # Sortiere nach Signalstärke (stärkstes Signal zuerst)
        networks.sort(key=lambda x: x['rssi'], reverse=True)
        
        return networks
    
    except Exception as e:
        print(f"Fehler beim Scannen: {e}")
        return []
    
    finally:
        # LED ausschalten
        led.value = False

def clear_pixels():
    """Alle NeoPixels ausschalten"""
    pixels.fill((0, 0, 0))
    pixels.show()

def display_mode_1(networks):
    """Zeigt die Signalstärke der ersten 6 Netzwerke an"""
    clear_pixels()
    
    # Zeige maximal NUM_PIXELS Netzwerke an
    for i in range(min(len(networks), NUM_PIXELS)):
        signal_strength = networks[i]['rssi']
        color = map_signal_to_color(signal_strength)
        pixels[i] = color
    
    pixels.show()
    
    # Netzwerkinformationen ausgeben
    print("\nGefundene WLAN-Netzwerke:")
    for i, network in enumerate(networks[:NUM_PIXELS]):
        print(f"{i+1}. {network['ssid']}: {network['rssi']} dBm (Kanal {network['channel']})")

def display_mode_2(networks):
    """Zeigt die Details eines Netzwerks mit allen LEDs an"""
    if not networks:
        clear_pixels()
        return
    
    # Verwende das stärkste Netzwerk
    network = networks[0]
    signal_index = get_signal_index(network['rssi'])
    
    # Zeige Signalstärke als Balkenanzeige
    clear_pixels()
    for i in range(NUM_PIXELS):
        if i <= signal_index:
            pixels[i] = SIGNAL_COLORS[i]
        else:
            pixels[i] = (0, 0, 0)
    
    pixels.show()
    
    # Netzwerkinformationen ausgeben
    print(f"\nDetailsansicht für: {network['ssid']}")
    print(f"Signalstärke: {network['rssi']} dBm (Kanal {network['channel']})")
    print(f"Qualität: {signal_index + 1}/6")

def button_released():
    """Erkennt, ob der Taster gedrückt und losgelassen wurde"""
    if not button.value:  # Taster ist gedrückt (LOW wegen Pull-up)
        time.sleep(0.1)  # Entprellen
        while not button.value:
            pass  # Warte, bis der Taster losgelassen wird
        time.sleep(0.1)  # Entprellen
        return True
    return False

# Hauptprogramm
print("WLAN-Signalstärke-Anzeige gestartet")
print("Drücke den Taster, um zwischen Anzeigemodi zu wechseln")

# Blinken zum Start
for _ in range(3):
    led.value = True
    time.sleep(0.1)
    led.value = False
    time.sleep(0.1)

try:
    mode = 1  # Anzeigemodus (1 = Mehrere Netzwerke, 2 = Einzelnes Netzwerk)
    
    while True:
        # Überprüfe Tasterdruck für Moduswechsel
        if button_released():
            mode = 3 - mode  # Wechsle zwischen 1 und 2
            print(f"Modus gewechselt: {mode}")
            
            # Feedback über LEDs
            clear_pixels()
            pixels[mode-1] = (0, 0, 255)  # Blaue LED zeigt Modus an
            pixels.show()
            time.sleep(0.5)
        
        # Scanne nach WLAN-Netzwerken
        networks = scan_wifi()
        
        # Zeige gefundene Netzwerke im aktuellen Modus an
        if mode == 1:
            display_mode_1(networks)
        else:
            display_mode_2(networks)
        
        # Warte vor dem nächsten Scan
        print(f"\nNächster Scan in {SCAN_INTERVAL} Sekunden...")
        time.sleep(SCAN_INTERVAL)

except KeyboardInterrupt:
    print("\nProgramm beendet.")
    clear_pixels()
