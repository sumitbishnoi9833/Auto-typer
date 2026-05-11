import time
import re
import os
import sys

# VERSION: 18

def modify_self():
    file_path = os.path.abspath(__file__)

    with open(file_path, "r") as f:
        code = f.read()

    # Find version number
    match = re.search(r"# VERSION: (\d+)", code)

    if match:
        current_version = int(match.group(1))
        new_version = current_version + 1

        print(f"Changing version {current_version} -> {new_version}")

        # Replace old version with new version
        updated_code = re.sub(
            r"# VERSION: \d+",
            f"# VERSION: {new_version}",
            code
        )

        # Save modified code
        with open(file_path, "w") as f:
            f.write(updated_code)

        print("Code updated!")

while True:
    modify_self()

    print("Waiting 10 minutes...")
    time.sleep(6)  # 600 sec = 10 mins

    # Restart itself
    os.execv(sys.executable, ['python'] + sys.argv)