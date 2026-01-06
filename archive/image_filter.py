import re
import logging
import asyncio
from io import BytesIO
from typing import Optional, List, Dict
from dataclasses import dataclass
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

@dataclass
class SuspiciousPattern:
    """Паттерн подозрительного контента"""
    keywords: List[str]
    context_keywords: List[str]
    severity: str  # 'high', 'medium', 'low'
    description: str

# База паттернов скама
SCAM_PATTERNS = [
    SuspiciousPattern(
        keywords=['withdrawal', 'successful', '$', 'usdt', 'received', 'withdraw'],
        context_keywords=['congratulations', 'money', 'transfer', 'wallet'],
        severity='high',
        description='Фейковое уведомление о выводе криптовалюты'
    ),
    SuspiciousPattern(
        keywords=['reward', 'claim', 'bonus', 'free', 'gift'],
        context_keywords=['limited', 'exclusive', 'now', 'hurry', 'click'],
        severity='high',
        description='Фишинг с обещанием награды'
    ),
    SuspiciousPattern(
        keywords=['verify', 'account', 'suspended', 'action required'],
        context_keywords=['immediately', 'urgent', 'security', 'confirm'],
        severity='high',
        description='Фишинг под видом верификации'
    ),
    SuspiciousPattern(
        keywords=['investment', 'profit', 'guaranteed', 'earn', 'passive income'],
        context_keywords=['join', 'team', 'money', 'daily', 'unlimited'],
        severity='medium',
        description='Финансовая пирамида'
    ),
    SuspiciousPattern(
        keywords=['dating', 'meet', 'lonely', 'single', 'girls'],
        context_keywords=['waiting', 'nearby', 'tonight', 'free'],
        severity='medium',
        description='Сомнительные знакомства'
    ),
    SuspiciousPattern(
        keywords=['elon musk', 'илон маск'],
        context_keywords=['crypto', 'giveaway', 'promo', 'bonus', 'free', 'крипто', 
                         'раздача', 'промо', 'бонус', 'бесплатно', 'криптовалюта'],
        severity='medium',
        description='Мошенничество с трудоустройством'
    ),
]

# Предкомпилированные регулярные выражения для производительности
EMOJI_PATTERN = re.compile(r'[🎁💰💸💵💴💶💷🤑💳💎🏆🎉✨⭐🌟]')
MONEY_PATTERN = re.compile(r'\$\d+[,.]?\d*|\d+\s*(usdt|btc|eth)', re.IGNORECASE)
URGENCY_WORDS = {'urgent', 'now', 'limited', 'hurry', 'expires', 'срочно', 'быстрее'}


class ImageScamDetector:
    """Детектор скама в изображениях"""
    
    def __init__(self, ocr_languages=['en', 'ru'], max_workers=2):
        self.ocr_languages = ocr_languages
        self._ocr_reader = None
        self._ocr_lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._initialization_task = None
    
    async def _init_ocr(self):
        """Ленивая инициализация OCR с защитой от повторной инициализации"""
        async with self._ocr_lock:
            if self._ocr_reader is not None:
                return
            
            try:
                import easyocr
                # Инициализация в отдельном потоке
                self._ocr_reader = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: easyocr.Reader(self.ocr_languages, gpu=False, verbose=False)
                )
                logging.info("EasyOCR инициализирован")
            except ImportError:
                # Fallback на pytesseract
                self._ocr_reader = 'pytesseract'
                logging.info("Используется pytesseract")
    
    async def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Извлекает текст из изображения"""
        # Предварительная проверка размера
        if len(image_bytes) > 10 * 1024 * 1024:  # Лимит 10MB
            logging.warning("Изображение слишком большое, пропускаем OCR")
            return ""
        
        await self._init_ocr()
        
        try:
            if self._ocr_reader == 'pytesseract':
                import pytesseract
                from PIL import Image
                
                image = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: Image.open(BytesIO(image_bytes))
                )
                
                text = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: pytesseract.image_to_string(image)
                )
            else:
                # EasyOCR с таймаутом
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        self._executor,
                        lambda: self._ocr_reader.readtext(image_bytes)
                    ),
                    timeout=30.0  # Таймаут 30 секунд
                )
                text = ' '.join([detection[1] for detection in result])
            
            return text.lower()
            
        except asyncio.TimeoutError:
            logging.error("OCR timeout exceeded")
            return ""
        except Exception as e:
            logging.error(f"Error extracting text: {e}")
            return ""
    
    @lru_cache(maxsize=128)
    def _check_pattern_cached(self, text: str, pattern_idx: int) -> Optional[Dict]:
        """Кешированная проверка паттерна"""
        pattern = SCAM_PATTERNS[pattern_idx]
        
        # Подсчитываем совпадения
        keyword_matches = sum(1 for kw in pattern.keywords if kw.lower() in text)
        context_matches = sum(1 for kw in pattern.context_keywords if kw.lower() in text)
        
        # Пороги для срабатывания
        min_keywords = 2 if pattern.severity == 'high' else 3
        min_context = 1 if pattern.severity == 'high' else 2
        
        if keyword_matches >= min_keywords and context_matches >= min_context:
            return {
                'pattern': pattern.description,
                'severity': pattern.severity,
                'keyword_matches': keyword_matches,
                'context_matches': context_matches,
                'confidence': min(
                    (keyword_matches + context_matches) / 
                    (len(pattern.keywords) + len(pattern.context_keywords)),
                    1.0
                )
            }
        
        return None
    
    def _check_visual_indicators(self, text: str) -> List[str]:
        """Проверяет визуальные индикаторы скама (оптимизировано)"""
        indicators = []
        
        # Множественные emoji
        emoji_count = len(EMOJI_PATTERN.findall(text))
        if emoji_count > 5:
            indicators.append('Excessive emoji usage')
        
        # КАПС (оптимизировано)
        if text:
            caps_count = sum(1 for c in text if c.isupper())
            if caps_count / len(text) > 0.3:
                indicators.append('Excessive capitalization')
        
        # Восклицательные знаки
        if text.count('!') > 3:
            indicators.append('Excessive exclamation marks')
        
        # Суммы денег
        if MONEY_PATTERN.search(text):
            indicators.append('Money amounts mentioned')
        
        # Срочность
        text_lower = text.lower()
        if any(word in text_lower for word in URGENCY_WORDS):
            indicators.append('Urgency tactics')
        
        return indicators
    
    async def analyze_image(self, image_bytes: bytes) -> Optional[Dict]:
        """Анализирует изображение на наличие скама"""
        try:
            # Извлекаем текст
            text = await self.extract_text_from_image(image_bytes)
            
            logging.info(f"Извлечённый текст: {text[:100]}...")
            
            # Пропускаем пустые изображения
            if len(text.strip()) < 10:
                return None
            
            # Проверяем паттерны параллельно
            pattern_tasks = [
                asyncio.create_task(
                    asyncio.to_thread(self._check_pattern_cached, text, i)
                )
                for i in range(len(SCAM_PATTERNS))
            ]
            
            pattern_results = await asyncio.gather(*pattern_tasks, return_exceptions=True)
            detected_patterns = [
                r for r in pattern_results 
                if r and not isinstance(r, Exception)
            ]
            
            # Проверяем визуальные индикаторы
            visual_indicators = await asyncio.to_thread(
                self._check_visual_indicators, text
            )
            
            # Если есть совпадения
            if detected_patterns or len(visual_indicators) >= 2:
                return {
                    'is_suspicious': True,
                    'detected_patterns': detected_patterns,
                    'visual_indicators': visual_indicators,
                    'extracted_text': text[:200],
                    'max_severity': max(
                        (p['severity'] for p in detected_patterns),
                        default='low'
                    )
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Error analyzing image: {e}")
            return None
    
    async def close(self):
        """Освобождение ресурсов"""
        self._executor.shutdown(wait=False)


class MediaMessageChecker:
    """Проверка сообщений с медиа"""
    
    def __init__(self, max_workers=2):
        self.image_detector = ImageScamDetector(max_workers=max_workers)
    
    async def check_message_with_media(
        self, 
        text: str, 
        attachments: List[bytes],
        max_images: int = 3
    ) -> Optional[Dict]:
        """
        Комплексная проверка сообщения с медиа
        
        Args:
            text: Текст сообщения
            attachments: Байты прикрепленных изображений
            max_images: Максимальное количество изображений для проверки
        """
        results = {
            'text_suspicious': False,
            'images_suspicious': False,
            'details': []
        }
        
        # Создаем задачи
        tasks = []
        
        # 1. Проверяем текст (если есть)
        if text and len(text.strip()) > 0:
            async def check_text():
                try:
                    from modules.automod.link_filter import detect_links
                    link_result = await detect_links(text)
                    if link_result:
                        return {
                            'type': 'text',
                            'reason': link_result,
                            'suspicious': True
                        }
                except ImportError:
                    logging.warning("Link filter module not found")
                return None
            
            tasks.append(check_text())
        
        # 2. Проверяем изображения параллельно (с лимитом)
        limited_attachments = attachments[:max_images]
        
        for idx, attachment_bytes in enumerate(limited_attachments):
            async def check_image(img_bytes, img_idx):
                result = await self.image_detector.analyze_image(img_bytes)
                if result and result['is_suspicious']:
                    return {
                        'type': 'image',
                        'index': img_idx,
                        'analysis': result,
                        'suspicious': True
                    }
                return None
            
            tasks.append(check_image(attachment_bytes, idx))
        
        # Выполняем все проверки параллельно
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for result in task_results:
            if result and not isinstance(result, Exception):
                if result.get('suspicious'):
                    results['details'].append(result)
                    if result['type'] == 'text':
                        results['text_suspicious'] = True
                    elif result['type'] == 'image':
                        results['images_suspicious'] = True
        
        # 3. Эвристика: только картинка без текста = подозрительно
        if (not text or len(text.strip()) < 5) and attachments:
            results['details'].append({
                'type': 'heuristic',
                'reason': 'Image-only message (common scam tactic)'
            })
        
        # Итоговая оценка
        is_suspicious = results['text_suspicious'] or results['images_suspicious']
        
        return results if is_suspicious else None
    
    async def close(self):
        """Освобождение ресурсов"""
        await self.image_detector.close()


# Глобальный экземпляр
media_message_checker = MediaMessageChecker()