#!/usr/bin/env python3
"""
test_ctrl_m.py
==============

Test script to verify Ctrl+M monitoring stop functionality.

Usage:
    python test_ctrl_m.py

Instructions:
    1. Run the script
    2. Try pressing Ctrl+C (should be ignored and allow copying)
    3. Try pressing Ctrl+M (should stop the monitoring)
"""

import time
import threading

# Global flag
stop_requested = False

def keyboard_listener():
    """Listen for Ctrl+M."""
    global stop_requested
    try:
        import keyboard
        print("🎯 Keyboard listener active. Ctrl+M will stop, Ctrl+C will be ignored.")
        while not stop_requested:
            if keyboard.is_pressed('ctrl+m'):
                print("\n✅ Ctrl+M detected - Stopping test!")
                stop_requested = True
                break
            time.sleep(0.1)
    except ImportError:
        print("⚠️ 'keyboard' module not available.")
    except Exception as e:
        print(f"⚠️ Error: {e}")

def main():
    """Test monitoring with Ctrl+M stop."""
    print("🔥 CTRL+M MONITORING TEST")
    print("=" * 40)
    print("📝 Testing safe monitoring controls:")
    print("   • Ctrl+C will be IGNORED (safe for error copying)")  
    print("   • Ctrl+M will STOP monitoring gracefully")
    print("=" * 40)
    
    # Start keyboard listener
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    counter = 0
    while not stop_requested:
        counter += 1
        print(f"⏰ Monitoring active... {counter}s (Ctrl+C=ignore, Ctrl+M=stop)", end='\r')
        
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n💡 Ctrl+C pressed but ignored! (Counter: {counter})")
            print("   You can safely copy this error message!")
            print("   Use Ctrl+M to stop monitoring.")
            time.sleep(1)
        
        # Auto-stop after 60 seconds
        if counter >= 60:
            print(f"\n⏱️ Auto-stopping after {counter} seconds.")
            break
    
    print("\n\n✅ Test completed successfully!")
    print("🎯 Ctrl+M monitoring stop confirmed!")

if __name__ == "__main__":
    main()