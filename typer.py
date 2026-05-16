import time
import subprocess

time.sleep(5)

with open("code.txt", "r", encoding="utf-8") as f:
    for line in f:
        subprocess.run([
            "xdotool",
            "type",
            "--delay",
            "11",
            line.rstrip()
        ])

        subprocess.run([
            "xdotool",
            "key",
            "Return"
        ])

        time.sleep(0.1)