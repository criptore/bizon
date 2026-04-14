import platform
import psutil
import json
import logging
import subprocess

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("hardware_detector")

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def get_cpu_info():
    """Detect CPU details including physical/logical cores and frequency."""
    freq_current = "Unknown"
    try:
        freq = psutil.cpu_freq()
        if freq and getattr(freq, 'current', 0) > 0:
            freq_current = freq.current
        elif platform.system() == "Darwin":
            # Fallback for some macOS systems via sysctl
            try:
                out = subprocess.check_output(["sysctl", "-n", "hw.cpufrequency"]).decode("utf-8").strip()
                freq_current = round(int(out) / 1e6, 2)  # Convert to MHz
            except Exception:
                freq_current = "Apple Silicon (no freq exposed)"
    except Exception as e:
        logger.debug(f"Could not retrieve CPU frequency: {e}")

    return {
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical": psutil.cpu_count(logical=True),
        "frequency_mhz": freq_current
    }


def get_ram_info():
    """Detect RAM details (total, available, used percentage)."""
    vm = psutil.virtual_memory()
    return {
        "total_gb": round(vm.total / (1024**3), 2),
        "available_gb": round(vm.available / (1024**3), 2),
        "percent_used": vm.percent
    }


def get_gpu_info():
    """Detect GPU specifics: CUDA, Apple MPS, or CPU fallback."""
    info = {"device": "CPU", "details": None}
    
    if HAS_TORCH:
        if torch.cuda.is_available():
            info["device"] = "CUDA"
            info["details"] = torch.cuda.get_device_name(0)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            info["device"] = "MPS"
            info["details"] = "Apple Silicon GPU (MPS)"
            
    return info


def get_os_info():
    """Get basic OS information."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine()
    }


def adapt_parameters(hw_info):
    """Adapt Bizon parameters based on detected hardware."""
    ram_gb = hw_info["ram"]["total_gb"]
    gpu_type = hw_info["gpu"]["device"]
    cpu_cores = hw_info["cpu"]["cores_physical"] or 2
    
    adaptation = {}
    
    # Adapt batch size and parallelism
    if gpu_type in ("CUDA", "MPS") and ram_gb >= 16:
        adaptation["batch_size"] = 64
        adaptation["calc_frequency_ms"] = 50
    elif ram_gb >= 8:
        adaptation["batch_size"] = 32
        adaptation["calc_frequency_ms"] = 100
    else:
        adaptation["batch_size"] = 16
        adaptation["calc_frequency_ms"] = 200
        
    adaptation["workers"] = max(1, cpu_cores - 1)
    
    return adaptation


def detect_hardware():
    """Run full hardware detection and return adaptation profile."""
    logger.info("Starting local hardware detection...")
    
    hw_info = {
        "os": get_os_info(),
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "gpu": get_gpu_info()
    }
    
    hw_info["adaptation"] = adapt_parameters(hw_info)
    
    return hw_info


def main():
    hw_report = detect_hardware()
    report_json = json.dumps(hw_report, indent=4)
    print("\n--- Bizon Hardware Report ---")
    print(report_json)
    print("-----------------------------\n")
    return report_json


if __name__ == "__main__":
    main()
