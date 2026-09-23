import re
from core.deepl_translator import DeepLTranslator, preprocess_text
from core.browser_translator import BrowserTranslator

JP_CHAR_REGEX = re.compile(r"[\u3041-\u3096\u30a1-\u30fa\u4e00-\u9faf]")

class HybridTranslator:
    def __init__(self, engine: str = "deepl"):
        self.engine_name = engine
        self._deepl = None
        self._fallback = None

    def __enter__(self):
        if self.engine_name == "deepl":
            self._deepl = DeepLTranslator()
            self._deepl.__enter__()
        else:
            self._fallback = BrowserTranslator()
            self._fallback.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._deepl:
            self._deepl.__exit__(exc_type, exc_val, exc_tb)
        if self._fallback:
            self._fallback.__exit__(exc_type, exc_val, exc_tb)

    def translate_lines(self, lines, source_lang="ja", target_lang="kk"):
        if self._deepl:
            return self._deepl.translate_lines(lines, source_lang=source_lang, target_lang=target_lang)
        elif self._fallback:
            return self._fallback.translate_lines(lines, source_lang=source_lang, target_lang=target_lang)
        return lines

Translator = HybridTranslator
preprocess_japanese_text = preprocess_text

__all__ = ["Translator", "HybridTranslator", "DeepLTranslator", "BrowserTranslator", "preprocess_text", "preprocess_japanese_text"]
