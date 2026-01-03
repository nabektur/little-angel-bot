import asyncio
import time
from typing import Dict, Tuple
from contextlib import asynccontextmanager

class LockManagerWithIdleTTL:
    def __init__(self, idle_ttl: int = 3600):
        self._locks: Dict[int, Tuple[asyncio.Lock, float]] = {}
        self._creation_lock = asyncio.Lock()
        self._idle_ttl = idle_ttl
        self._cleanup_task = None
    
    def start_cleanup(self):
        """Запуск фоновой задачи очистки"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Периодическая очистка неиспользуемых asyncio.Lock"""
        while True:
            await asyncio.sleep(60)  # Проверка каждую минуту
            now = time.time()
            async with self._creation_lock:
                expired = [
                    uid for uid, (lock, last_used) in self._locks.items()
                    if now - last_used >= self._idle_ttl and not lock.locked()
                ]
                for uid in expired:
                    del self._locks[uid]
    
    async def get_lock(self, user_id: int) -> asyncio.Lock:
        """Получить лок и обновить время последнего использования"""
        now = time.time()
        
        # Быстрая проверка без блокировки
        if user_id in self._locks:
            lock, _ = self._locks[user_id]
            self._locks[user_id] = (lock, now)  # Обновляет last_used
            return lock
        
        # Создание нового лока
        async with self._creation_lock:
            if user_id in self._locks:
                lock, _ = self._locks[user_id]
                self._locks[user_id] = (lock, now)
                return lock
            
            new_lock = asyncio.Lock()
            self._locks[user_id] = (new_lock, now)
            return new_lock
    
    @asynccontextmanager
    async def lock(self, user_id: int):
        """Контекстный менеджер для удобного использования"""
        lock = await self.get_lock(user_id)
        async with lock:
            yield
        # После освобождения обновляет last_used
        if user_id in self._locks:
            self._locks[user_id] = (self._locks[user_id][0], time.time())