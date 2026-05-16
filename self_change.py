import time
import re
import os
import sys

# VERSION: 412

def modify_self():
    file_path = os.path.abspath(__file__)

    with open(file_path, "r") as f:
        code = f.read()

    
    match = re.search(r"# VERSION: (\d+)", code)

    if match:
        current_version = int(match.group(1))
        new_version = current_version + 1

        print(f"Changing version {current_version} -> {new_version}")

       
        updated_code = re.sub(
            r"# VERSION: \d+",
            f"# VERSION: {new_version}",
            code
        )

        
        with open(file_path, "w") as f:
            f.write(updated_code)

        print("Code updated!")

while True:
    modify_self()

    print("Waiting 10 minutes...")
    time.sleep(1)  

 
    os.execv(sys.executable, ['python'] + sys.argv)