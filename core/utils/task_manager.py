import hashlib
import threading
from datetime import datetime
from typing import Callable, Any, Dict

class TaskManager:
    def __init__(self):
        self.cache_lock = threading.Lock()
        self.long_query_cache: Dict[str, Dict[str, Any]] = {}

    def generate_request_hash(self, request_model: Any) -> str:
        """
        Genera un hash único para un modelo de solicitud.
        """
        return hashlib.md5(str(request_model.dict()).encode()).hexdigest()

    def _async_query_task(self, request_hash: str, request_model: Any, func: Callable[..., Any], **kwargs: Any):
        """
        Ejecuta una función en segundo plano y almacena su resultado en el caché.
        """
        try:
            with self.cache_lock:
                self.long_query_cache[request_hash] = {"status": "processing", "updated_at": datetime.now().isoformat()}
            result = func(request_model, **kwargs)
            with self.cache_lock:
                # Asumiendo que el resultado tiene un método .to_dict() si es un DataFrame
                # o es directamente serializable a JSON.
                # Si 'result' es un DataFrame de pandas, lo convertimos a una lista de diccionarios.
                if hasattr(result, 'to_dict') and callable(getattr(result, 'to_dict')):
                    result_data = result.to_dict(orient="records")
                else:
                    result_data = result # Asumir que ya es serializable

                self.long_query_cache[request_hash] = {"status": "finished", "updated_at": datetime.now().isoformat(), "data": result_data}

        except Exception as e:
            with self.cache_lock:
                self.long_query_cache[request_hash] = {"status": "error", "message": str(e), "updated_at": datetime.now().isoformat()}

    def check_or_start_task(self, request_model: Any, func: Callable[..., Any], **kwargs: Any) -> Dict[str, Any]:
        """
        Verifica si una tarea ya está en caché o la inicia en un nuevo hilo.
        """
        request_hash = self.generate_request_hash(request_model)
        with self.cache_lock:
            if request_hash in self.long_query_cache:
                return self.long_query_cache[request_hash]
        
        # Iniciar la tarea en un hilo separado
        thread = threading.Thread(target=self._async_query_task, args=(request_hash, request_model, func), kwargs=kwargs)
        thread.start()
        
        with self.cache_lock:
            # Asegurarse de que el estado "processing" se establezca antes de devolver
            if request_hash not in self.long_query_cache:
                self.long_query_cache[request_hash] = {"status": "processing", "updated_at": datetime.now().isoformat()}
            return self.long_query_cache[request_hash]

    def get_task_status(self, request_hash: str) -> Dict[str, Any]:
        """
        Obtiene el estado actual de una tarea del caché.
        """
        with self.cache_lock:
            return self.long_query_cache.get(request_hash, {"status": "not_found", "message": "Task not found"})

# Instancia global del TaskManager para ser utilizada en toda la aplicación
task_manager = TaskManager()
