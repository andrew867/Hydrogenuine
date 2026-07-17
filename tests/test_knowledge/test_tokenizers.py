#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for language-specific tokenizers.

Test-driven development: Write tests BEFORE implementing tokenizers.py
"""

import sys
from pathlib import Path

import pytest


class TestTokenizerRegistry:
    """Test tokenizer registry and selection"""
    
    def test_get_tokenizer_for_english(self):
        """Test getting tokenizer for English"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("en")
        assert tokenizer is not None, "Should return tokenizer for English"
        
        # Test tokenization
        text = "Artificial intelligence is a branch of computer science"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize text"
        assert "artificial" in tokens or "Artificial" in tokens, "Should include 'artificial'"
    
    def test_get_tokenizer_for_chinese(self):
        """Test getting tokenizer for Chinese"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("zh")
        assert tokenizer is not None, "Should return tokenizer for Chinese"
        
        # Test tokenization (Chinese needs word segmentation)
        text = "人工智能是计算机科学的一个分支"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize Chinese text"
        # Should segment into words, not just characters
        assert any(len(token) > 1 for token in tokens), "Should segment into words"
    
    def test_get_tokenizer_for_japanese(self):
        """Test getting tokenizer for Japanese"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("ja")
        assert tokenizer is not None, "Should return tokenizer for Japanese"
        
        # Test tokenization
        text = "人工知能はコンピュータサイエンスの一分野です"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize Japanese text"
    
    def test_get_tokenizer_for_spanish(self):
        """Test getting tokenizer for Spanish"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("es")
        assert tokenizer is not None, "Should return tokenizer for Spanish"
        
        # Test tokenization
        text = "La inteligencia artificial es una rama de la informática"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize Spanish text"
        assert "inteligencia" in tokens or "inteligencia".lower() in [t.lower() for t in tokens], "Should include 'inteligencia'"
    
    def test_get_tokenizer_for_arabic(self):
        """Test getting tokenizer for Arabic"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("ar")
        assert tokenizer is not None, "Should return tokenizer for Arabic"
        
        # Test tokenization
        text = "الذكاء الاصطناعي هو فرع من علوم الكمبيوتر"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize Arabic text"
    
    def test_get_tokenizer_for_korean(self):
        """Test getting tokenizer for Korean"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("ko")
        assert tokenizer is not None, "Should return tokenizer for Korean"
        
        # Test tokenization
        text = "인공지능은 컴퓨터 과학의 한 분야입니다"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize Korean text"
    
    def test_get_tokenizer_for_unknown_language(self):
        """Test fallback tokenizer for unknown language"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("xx")  # Unknown language code
        assert tokenizer is not None, "Should return fallback tokenizer"
        
        # Test tokenization
        text = "Some text in unknown language"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize text even for unknown language"


class TestChineseTokenizer:
    """Test Chinese tokenizer specifically (jieba)"""
    
    def test_chinese_word_segmentation(self):
        """Test that Chinese tokenizer segments words correctly"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("zh")
        
        # "人工智能" should be segmented as one word, not two characters
        text = "人工智能"
        tokens = tokenizer.tokenize(text)
        
        # Should segment into meaningful words
        assert len(tokens) >= 1, "Should segment into at least one token"
        # Check that it's not just character-by-character
        assert any(len(token) >= 2 for token in tokens), "Should segment into multi-character words"
    
    def test_chinese_with_english(self):
        """Test Chinese tokenizer with mixed Chinese-English text"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("zh")
        
        text = "AI（人工智能）技术"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize mixed text"


class TestUnicodeHandling:
    """Test Unicode and emoji handling in tokenizers"""
    
    def test_emoji_in_text(self):
        """Test that tokenizers handle emojis"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("en")
        
        text = "AI 🤖 and machine learning 🧠 are fascinating"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        # Emojis should be preserved or handled gracefully
        assert len(tokens) > 0, "Should tokenize text with emojis"
    
    def test_special_characters(self):
        """Test that tokenizers handle special characters"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("en")
        
        text = "AI (artificial intelligence) & ML (machine learning)"
        tokens = tokenizer.tokenize(text)
        
        assert isinstance(tokens, list), "Should return list of tokens"
        assert len(tokens) > 0, "Should tokenize text with special characters"
    
    def test_normalization(self):
        """Test that tokenizers normalize text"""
        from skills.knowledge.tokenizers import get_tokenizer
        
        tokenizer = get_tokenizer("en")
        
        # Test with different Unicode forms
        text1 = "café"  # Normal form
        text2 = "cafe\u0301"  # Combined form
        
        tokens1 = tokenizer.tokenize(text1)
        tokens2 = tokenizer.tokenize(text2)
        
        # Should normalize to same tokens
        assert tokens1 == tokens2, "Should normalize Unicode to same tokens"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
