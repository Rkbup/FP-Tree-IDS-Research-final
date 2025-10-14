#!/usr/bin/env python3
"""
test_signal_handling.py
=======================

Test script to verify that Ctrl+C is ignored and Ctrl+H triggers graceful shutdown.

Usage:
    python test_signal_handling.py

Instructions:
    1. Run the script
    2. Try pressing Ctrl+C (should be ignored)
    3. Try pressing Ctrl+H (should trigger graceful shutdown)
"""

import signal
import time
import threading
import sys

# Global flag for graceful shutdown
shutdown_requested = False

def ctrl_c_handler(signum, frame):
    """Handle Ctrl+C - Do nothing (ignore it)."""
    print("\n💡 Ctrl+C detected but IGNORED! Use Ctrl+H to stop gracefully.")
    print("   This allows safe copying of error messages without interrupting the process.")

def shutdown_handler():
    """Handle Ctrl+H for graceful shutdown."""
    global shutdown_requested
    try:
        import keyboard
        print("🎯 Keyboard listener started. Press Ctrl+H to stop gracefully.")
        while True:
            if keyboard.is_pressed('ctrl+h'):
                if not shutdown_requested:
                    print("\n\n✅ Ctrl+H detected - Graceful shutdown initiated!")
                    shutdown_requested = True
                break
            time.sleep(0.1)
    except ImportError:
        print("⚠️  Warning: 'keyboard' module not installed. Ctrl+H functionality not available.")
        print("   Only terminal-based shutdown will work.")
    except Exception as e:
        print(f"⚠️  Keyboard listener error: {e}")

def main():
    """Main test function."""
    print("🔥 SIGNAL HANDLING TEST")
    print("=" * 40)
    print("📝 Testing new signal handling:")
    print("   • Ctrl+C will be IGNORED (safe for copying errors)")
    print("   • Ctrl+H will trigger GRACEFUL SHUTDOWN")
    print("=" * 40)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, ctrl_c_handler)  # Ignore Ctrl+C
    
    # Start keyboard listener for Ctrl+H
    keyboard_thread = threading.Thread(target=shutdown_handler, daemon=True)
    keyboard_thread.start()
    
    print("🚀 Test process started...")
    print("💡 Try pressing Ctrl+C (should be ignored)")
    print("💡 Try pressing Ctrl+H (should stop the process)")
    print()
    
    counter = 0
    while not shutdown_requested:
        counter += 1
        print(f"⏰ Running... {counter} seconds (Ctrl+C=ignore, Ctrl+H=stop)", end='\r')
        time.sleep(1)
        
        # Auto-stop after 120 seconds for safety
        if counter >= 120:
            print(f"\n⏱️  Auto-stopping after {counter} seconds for safety.")
            break
    
    print("\n\n✅ Process completed gracefully!")
    print("🎯 Signal handling test successful!")

if __name__ == "__main__":
    main()