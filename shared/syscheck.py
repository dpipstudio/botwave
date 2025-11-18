import os
import sys
from typing import Optional
from shared.logger import Log

def is_valid_executable(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)

def check_bakcends_paths() -> Optional[str]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path_file = os.path.join(current_dir, "..", "backend_path")
    
    if os.path.isfile(path_file):
        try:
            with open(path_file, "r") as file:
                path = file.read().strip()
                if is_valid_executable(path):
                    return path
                else:
                    Log.error("[Launcher] The path in backend_path is invalid.")
                    Log.info("[Launcher] Please relaunch this program.")
                    os.remove(path_file)
        except Exception as e:
            Log.error(f"Error reading {path_file}: {e}")
            os.remove(path_file)
    
    search_paths = ["/opt/BotWave/backends/bw_custom/src", "/opt", "/usr/local/bin", "/usr/bin", "/bin", "/home"]
    
    for directory in search_paths:
        if not os.path.isdir(directory):
            continue
        try:
            for root, _, files in os.walk(directory):
                if "bw_custom" in files:
                    path = os.path.join(root, "bw_custom")
                    if is_valid_executable(path):
                        with open(path_file, "w") as file:
                            file.write(path)
                        return path
        except Exception:
            pass
    
    Log.warning("Could not automatically find `bw_custom`. Please enter the full path manually.")
    user_path = input("Enter the path to `bw_custom`: ").strip()
    if is_valid_executable(user_path):
        with open(path_file, "w") as file:
            file.write(user_path)
        return user_path
    
    Log.error("The path you provided is not valid or `bw_custom` is not executable.")
    Log.info("Please make sure `bw_custom` is installed and accessible, then restart the program.")
    sys.exit(1)

def is_raspberry_pi() -> bool:
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        return 'Raspberry' in cpuinfo
    except:
        return False

def check_requirements(skip_checks: bool = False):
    if skip_checks:
        return
    
    if not is_raspberry_pi():
        Log.warning("This doesn't appear to be a Raspberry Pi")
        response = input("Continue anyway? (y/N): ").lower()
        if response != 'y':
            sys.exit(1)
    
    if os.geteuid() != 0:
        Log.error("This client must be run as root for GPIO access")
        sys.exit(1)
    
    pi_fm_rds_path = check_bakcends_paths()
    if not pi_fm_rds_path:
        Log.error("bw_custom not found. Please install PiFmRds first.")
        sys.exit(1)
    else:
        Log.success(f"Found bw_custom at: {pi_fm_rds_path}")