from pathlib import Path
import os
import sys
from typing import Optional

from shared.env import Env
from shared.logger import Log

def is_valid_executable(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)

def check_backends_paths() -> Optional[str]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(current_dir, "..", "backend_path")
    envpath = Env.get("BWCUSTOM_PATH")
    search_paths = [str(Path(envpath).parent)] if envpath else ["/opt/BotWave/backends/bw_custom/src", "/opt", "/usr/local/bin", "/usr/bin", "/bin", "/home"]
    exe_name = str(Path(envpath).name) if envpath else "bw_custom"
    
    if os.path.isfile(cache_file):
        if envpath:
            os.remove(cache_file) # skip cache if env is set

        else: 
            try:
                with open(cache_file, "r") as file:
                    path = file.read().strip()
                    if is_valid_executable(path):
                        return path
                    else:
                        Log.error("The path in backend_path is invalid.")
                        Log.info("Please relaunch this program. No other action is required from your end.")
                        os.remove(cache_file)

            except Exception as e:
                Log.error(f"Error reading {cache_file}: {e}")
                os.remove(cache_file)
    
    for directory in search_paths:
        if not os.path.isdir(directory):
            continue
        try:
            for root, _, files in os.walk(directory):
                if exe_name in files:
                    path = os.path.join(root, exe_name)
                    if is_valid_executable(path):
                        with open(cache_file, "w") as file:
                            file.write(path)
                        return path
                    
        except Exception:
            pass
    
    Log.warning(f"Could not automatically find `{exe_name}`. Please enter the full path manually.")
    user_path = input(f"Enter the path to `{exe_name}`: ").strip()
    if is_valid_executable(user_path):
        with open(cache_file, "w") as file:
            file.write(user_path)
        return user_path
    
    Log.error(f"The path you provided is not valid or `{exe_name}` is not executable.")
    Log.info(f"Please make sure `{exe_name}` is installed and accessible, then restart the program.")
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
    
    pi_fm_rds_path = check_backends_paths()
    if not pi_fm_rds_path:
        Log.error("Backend not found. Please install bw_custom first.")
        sys.exit(1)
    else:
        Log.success(f"Found backend at: {pi_fm_rds_path}")