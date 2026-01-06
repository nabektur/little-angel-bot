import re
import asyncio
from io          import BytesIO
from typing      import Optional, List, Dict
from dataclasses import dataclass

# Предполагаем использование библиотеки для OCR
# pip install easyocr pillow
# или pytesseract для более легковесного варианта

@dataclass
class SuspiciousPattern:
    """Паттерн подозрительного контента"""
    keywords: List[str]
    context_keywords: List[str]  # Дополнительные слова, усиливающие подозрение
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
        context_keywords=['crypto', 'giveaway', 'promo', 'bonus', 'free', 'крипто', 'раздача', 'промо', 'бонус', 'бесплатно', 'криптовалюта'],
        severity='medium',
        description='Мошенничество с трудоустройством'
    ),
]


class ImageScamDetector:
    """Детектор скама в изображениях"""
    
    def __init__(self, ocr_languages=['en', 'ru']):
        self.ocr_languages = ocr_languages
        self._ocr_reader = None
    
    async def _init_ocr(self):
        """Ленивая инициализация OCR"""
        if self._ocr_reader is None:
            try:
                import easyocr
                # Инициализация в отдельном потоке, т.к. это тяжелая операция
                self._ocr_reader = await asyncio.to_thread(
                    easyocr.Reader, self.ocr_languages, gpu=False
                )
            except ImportError:
                # Fallback на pytesseract
                import pytesseract
                self._ocr_reader = 'pytesseract'
    
    async def extract_text_from_image(self, image_object: BytesIO) -> str:
        """Извлекает текст из изображения"""
        await self._init_ocr()
        
        if self._ocr_reader == 'pytesseract':
            import pytesseract
            from PIL import Image
            image = Image.open(image_object)
            text = await asyncio.to_thread(pytesseract.image_to_string, image)
        else:
            # EasyOCR
            result = await asyncio.to_thread(
                self._ocr_reader.readtext, image_object
            )
            text = ' '.join([detection[1] for detection in result])
        
        return text.lower()
    
    def _check_pattern(self, text: str, pattern: SuspiciousPattern) -> Optional[Dict]:
        """Проверяет текст на соответствие паттерну"""
        # Подсчитываем совпадения
        keyword_matches = sum(1 for kw in pattern.keywords if kw.lower() in text)
        context_matches = sum(1 for kw in pattern.context_keywords if kw.lower() in text)
        
        # Пороги для срабатывания
        if pattern.severity == 'high':
            min_keywords = 2
            min_context = 1
        else:
            min_keywords = 3
            min_context = 2
        
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
        """Проверяет визуальные индикаторы скама"""
        indicators = []
        
        # Множественные emoji
        emoji_count = len(re.findall(r'[🎁💰💸💵💴💶💷🤑💳💎🏆🎉✨⭐🌟]', text))
        if emoji_count > 5:
            indicators.append('Excessive emoji usage')
        
        # КАПС
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.3:
            indicators.append('Excessive capitalization')
        
        # Восклицательные знаки
        exclamation_count = text.count('!')
        if exclamation_count > 3:
            indicators.append('Excessive exclamation marks')
        
        # Суммы денег
        if re.search(r'\$\d+[,.]?\d*', text) or re.search(r'\d+\s*(usdt|btc|eth)', text):
            indicators.append('Money amounts mentioned')
        
        # Срочность
        urgency_words = ['urgent', 'now', 'limited', 'hurry', 'expires', 'срочно', 'быстрее']
        if any(word in text.lower() for word in urgency_words):
            indicators.append('Urgency tactics')
        
        return indicators
    
    async def analyze_image(self, image_object: BytesIO) -> Optional[Dict]:
        """Анализирует изображение на наличие скама"""
        try:
            # Извлекаем текст
            text = await self.extract_text_from_image(image_object)
            
            # Пропускаем пустые изображения
            if len(text.strip()) < 10:
                return None
            
            # Проверяем паттерны
            detected_patterns = []
            for pattern in SCAM_PATTERNS:
                match = self._check_pattern(text, pattern)
                if match:
                    detected_patterns.append(match)
            
            # Проверяем визуальные индикаторы
            visual_indicators = self._check_visual_indicators(text)
            
            # Если есть совпадения
            if detected_patterns or len(visual_indicators) >= 2:
                return {
                    'is_suspicious': True,
                    'detected_patterns': detected_patterns,
                    'visual_indicators': visual_indicators,
                    'extracted_text': text[:200],  # Первые 200 символов
                    'max_severity': max(
                        [p['severity'] for p in detected_patterns],
                        default='low'
                    )
                }
            
            return None
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return None


# Дополнительные проверки для Discord/Telegram
class MediaMessageChecker:
    """Проверка сообщений с медиа"""
    
    def __init__(self):
        self.image_detector = ImageScamDetector()
    
    async def check_message_with_media(
        self, 
        text: str, 
        attachments: List[BytesIO]
    ) -> Optional[Dict]:
        """
        Комплексная проверка сообщения с медиа
        
        Args:
            text: Текст сообщения
            attachments: Пути к прикрепленным изображениям
        """
        results = {
            'text_suspicious': False,
            'images_suspicious': False,
            'details': []
        }
        
        # 1. Проверяем текст (если есть)
        if text and len(text.strip()) > 0:
            # Используем существующий детектор ссылок
            from modules.automod.link_filter import detect_links
            link_result = await detect_links(text)
            if link_result:
                results['text_suspicious'] = True
                results['details'].append({
                    'type': 'text',
                    'reason': link_result
                })
        
        # 2. Проверяем изображения
        for attachment_object in attachments:
            image_result = await self.image_detector.analyze_image(attachment_object)
            if image_result and image_result['is_suspicious']:
                results['images_suspicious'] = True
                results['details'].append({
                    'type': 'image',
                    'file': attachment_object.name,
                    'analysis': image_result
                })
        
        # 3. Эвристика: только картинка без текста = подозрительно
        if not text or len(text.strip()) < 5:
            if attachments:
                results['details'].append({
                    'type': 'heuristic',
                    'reason': 'Image-only message (common scam tactic)'
                })
        
        # Итоговая оценка
        is_suspicious = results['text_suspicious'] or results['images_suspicious']
        
        if is_suspicious:
            return results
        
        return None
    
media_message_checker = MediaMessageChecker()