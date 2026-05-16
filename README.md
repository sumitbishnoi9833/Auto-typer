Auto Typer

A fast Linux auto-typing script made with Python + xdotool.

It reads lines from a text file and types them automatically into any focused window with customizable speed.

Perfect for:

Typing practice demos
Automation
Repetitive text input
Code showcase videos
Testing editors/forms
Fun terminal projects
Features
Reads text from code.txt
Types automatically into focused window
Adjustable typing speed
Presses Enter after every line
Lightweight and simple
Works on Linux/X11
Arch Linux
sudo pacman -S xdotool
Ubuntu/Debian
sudo apt install xdotool
Setup

Clone the repo:

git clone https://github.com/sumit989bishnoi-crypto/Auto-typer.git
cd Auto-typer

Create text file:

nano code.txt

Add anything you want typed automatically.

Run
python typer.py

After running:

You get 5 seconds to focus your editor/window
Script starts typing automatically
Customize Speed

Change this value:

"--delay",
"11",

Lower = faster typing
Higher = slower typing
