import machine
import time

time.sleep(1)

try:
    import main
except ImportError:
    print("main.py not found!")

