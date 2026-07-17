#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for language detection.

Test-driven development: Write tests BEFORE implementing language_detector.py
"""

import sys
from pathlib import Path

import pytest


class TestLanguageDetection:
    """Test language detection functionality"""
    
    def test_detect_english(self):
        """Test detecting English text"""
        from skills.knowledge.language_detector import detect_language
        
        text = "Artificial intelligence is a branch of computer science"
        lang = detect_language(text)
        
        assert lang == "en", f"Should detect English, got {lang}"
    
    def test_detect_chinese(self):
        """Test detecting Chinese text"""
        from skills.knowledge.language_detector import detect_language, LANGDETECT_AVAILABLE
        
        text = "人工智能是计算机科学的一个分支"
        lang = detect_language(text)
        
        if LANGDETECT_AVAILABLE:
            assert lang == "zh", f"Should detect Chinese, got {lang}"
        else:
            # If langdetect not available, should default to English
            assert lang == "en", f"Should default to English when langdetect unavailable, got {lang}"
    
    def test_detect_japanese(self):
        """Test detecting Japanese text"""
        from skills.knowledge.language_detector import detect_language, LANGDETECT_AVAILABLE
        
        text = "人工知能はコンピュータサイエンスの一分野です"
        lang = detect_language(text)
        
        if LANGDETECT_AVAILABLE:
            assert lang == "ja", f"Should detect Japanese, got {lang}"
        else:
            assert lang == "en", f"Should default to English when langdetect unavailable, got {lang}"
    
    def test_detect_spanish(self):
        """Test detecting Spanish text"""
        from skills.knowledge.language_detector import detect_language, LANGDETECT_AVAILABLE
        
        text = "La inteligencia artificial es una rama de la informática"
        lang = detect_language(text)
        
        if LANGDETECT_AVAILABLE:
            assert lang == "es", f"Should detect Spanish, got {lang}"
        else:
            assert lang == "en", f"Should default to English when langdetect unavailable, got {lang}"
    
    def test_detect_arabic(self):
        """Test detecting Arabic text"""
        from skills.knowledge.language_detector import detect_language, LANGDETECT_AVAILABLE
        
        text = "الذكاء الاصطناعي هو فرع من علوم الكمبيوتر"
        lang = detect_language(text)
        
        if LANGDETECT_AVAILABLE:
            assert lang == "ar", f"Should detect Arabic, got {lang}"
        else:
            assert lang == "en", f"Should default to English when langdetect unavailable, got {lang}"
    
    def test_detect_korean(self):
        """Test detecting Korean text"""
        from skills.knowledge.language_detector import detect_language, LANGDETECT_AVAILABLE
        
        text = "인공지능은 컴퓨터 과학의 한 분야입니다"
        lang = detect_language(text)
        
        if LANGDETECT_AVAILABLE:
            assert lang == "ko", f"Should detect Korean, got {lang}"
        else:
            assert lang == "en", f"Should default to English when langdetect unavailable, got {lang}"
    
    def test_detect_thai(self):
        """Test detecting Thai text"""
        from skills.knowledge.language_detector import detect_language, LANGDETECT_AVAILABLE
        
        text = "ปัญญาประดิษฐ์เป็นสาขาหนึ่งของวิทยาการคอมพิวเตอร์"
        lang = detect_language(text)
        
        if LANGDETECT_AVAILABLE:
            assert lang == "th", f"Should detect Thai, got {lang}"
        else:
            assert lang == "en", f"Should default to English when langdetect unavailable, got {lang}"
    
    def test_mixed_language_defaults_to_english(self):
        """Test that mixed language text defaults to English"""
        from skills.knowledge.language_detector import detect_language
        
        text = "AI (人工智能) is a branch of computer science"
        lang = detect_language(text)
        
        # Should default to English for mixed content
        assert lang == "en", f"Mixed content should default to English, got {lang}"
    
    def test_short_text_defaults_to_english(self):
        """Test that very short text defaults to English"""
        from skills.knowledge.language_detector import detect_language
        
        text = "AI"
        lang = detect_language(text)
        
        assert lang == "en", f"Short text should default to English, got {lang}"
    
    def test_detection_confidence(self):
        """Test that detection returns confidence score"""
        from skills.knowledge.language_detector import detect_language_with_confidence, LANGDETECT_AVAILABLE
        
        text = "Artificial intelligence is a branch of computer science"
        result = detect_language_with_confidence(text)
        
        assert 'language' in result, "Should return language"
        assert 'confidence' in result, "Should return confidence"
        assert result['language'] == "en", "Should detect English"
        
        if LANGDETECT_AVAILABLE:
            assert result['confidence'] > 0.5, "Confidence should be reasonable"
        else:
            # When langdetect unavailable, confidence is 0.0
            assert result['confidence'] == 0.0, "Confidence should be 0.0 when langdetect unavailable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
