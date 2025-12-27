"""GPU 资源管理器 - 支持自动卸载"""
import threading
import time
import torch
import gc

class GPUManager:
    def __init__(self, idle_timeout=60):
        self.model = None
        self.transform = None
        self.lock = threading.Lock()
        self.last_used = 0
        self.idle_timeout = idle_timeout
        self._start_monitor()
    
    def _start_monitor(self):
        def monitor():
            while True:
                time.sleep(10)
                with self.lock:
                    if self.model and time.time() - self.last_used > self.idle_timeout:
                        self._offload()
        t = threading.Thread(target=monitor, daemon=True)
        t.start()
    
    def _offload(self):
        if self.model:
            del self.model
            self.model = None
            self.transform = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def get_model(self, load_func):
        with self.lock:
            if self.model is None:
                self.model, self.transform = load_func()
            self.last_used = time.time()
            return self.model, self.transform
    
    def force_offload(self):
        with self.lock:
            self._offload()
    
    def get_status(self):
        with self.lock:
            loaded = self.model is not None
        gpu_info = {}
        if torch.cuda.is_available():
            gpu_info = {
                "name": torch.cuda.get_device_name(0),
                "memory_used": torch.cuda.memory_allocated(0) / 1024**3,
                "memory_total": torch.cuda.get_device_properties(0).total_memory / 1024**3
            }
        return {"model_loaded": loaded, "gpu": gpu_info}

gpu_manager = GPUManager()
