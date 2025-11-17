from pathlib import Path
from typing import Optional
from shared.logger import Log

try:
    from pysstv.color import MODES
    MODE_MAP = {cls.__name__.lower(): cls for cls in MODES}
except ImportError:
    MODE_MAP = None
    MODES = None

def get_best_sstv_mode(width: int, height: int):
    if MODE_MAP is None or MODES is None:
        Log.error("PySSTV not installed")
        return None
    
    best = None
    best_score = 999999999
    
    for cls in MODES:
        try:
            dw = abs(cls.WIDTH - width)
            dh = abs(cls.HEIGHT - height)
        except:
            continue
        
        score = dw + dh
        if score < best_score:
            best_score = score
            best = cls
    
    return best

def make_sstv_wav(img_path: str, wav_path: str, mode_name: Optional[str] = None) -> bool:
    try:
        from PIL import Image
        import numpy as np
        import wave
    except ImportError:
        parent_parent = Path(__file__).parent.parent
        pip_path = parent_parent / "venv" / "bin" / "pip"
        Log.sstv("Please install required modules:")
        Log.sstv(f"{pip_path} install pysstv numpy pillow")
        return False
    
    if MODE_MAP is None:
        parent_parent = Path(__file__).parent.parent
        pip_path = parent_parent / "venv" / "bin" / "pip"
        Log.sstv("Please install required modules:")
        Log.sstv(f"{pip_path} install pysstv")
        return False
    
    try:
        img = Image.open(img_path).convert("RGB")
    except Exception as e:
        Log.sstv(f"Cannot open image: {e}")
        return False
    
    # Select mode
    if mode_name and mode_name.lower() in MODE_MAP:
        cls = MODE_MAP[mode_name.lower()]
    else:
        cls = get_best_sstv_mode(*img.size)
        if cls is None:
            return False
    
    # Resize image
    img = img.resize((cls.WIDTH, cls.HEIGHT))
    
    try:
        sstv = cls(img, 44100, 16)
        samples = np.array(list(sstv.gen_samples())).astype(np.int16)
        
        with wave.open(wav_path, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(44100)
            f.writeframes(samples.tobytes())
        
        Log.sstv(f"SSTV wav created {wav_path} (mode: {cls.__name__})")
        return True
    except Exception as e:
        Log.sstv(f"SSTV encode error: {e}")
        return False