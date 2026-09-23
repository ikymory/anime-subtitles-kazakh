"""Translator interface bridging to BrowserTranslator for high-quality natural Kazakh output."""
from core.browser_translator import BrowserTranslator, preprocess_text

Translator = BrowserTranslator
preprocess_japanese_text = preprocess_text

__all__ = ["Translator", "BrowserTranslator", "preprocess_text", "preprocess_japanese_text"]
