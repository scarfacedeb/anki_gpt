import pytest
from unittest.mock import Mock, patch
from chatgpt import get_definitions, extract_words, build_prompt
from word import Word, WordList


class TestChatGPTConfiguration:
    """Test the ChatGPT configuration and API calls"""
    
    def test_build_prompt(self):
        """Test that prompts are built correctly"""
        prompt = "Test prompt"
        input_text = "test input"
        result = build_prompt(prompt, input_text)
        
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == prompt
        assert result[1]["role"] == "user"
        assert result[1]["content"] == input_text

    @patch('chatgpt.OpenAI')
    def test_get_definitions_uses_gpt5_nano(self, mock_openai):
        """Test that get_definitions uses gpt-5-nano with low reasoning effort"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = WordList(words=[], context=None)
        mock_client.chat.completions.parse.return_value = mock_response
        mock_openai.return_value = mock_client
        
        result = get_definitions("test")
        
        # Verify the API call parameters
        mock_client.chat.completions.parse.assert_called_once()
        call_args = mock_client.chat.completions.parse.call_args
        
        assert call_args.kwargs['model'] == 'gpt-5-nano'
        assert call_args.kwargs['reasoning_effort'] == 'low'
        assert call_args.kwargs['response_format'] == WordList
        assert len(call_args.kwargs['messages']) == 2

    @patch('chatgpt.OpenAI')
    def test_extract_words_uses_gpt5_nano(self, mock_openai):
        """Test that extract_words uses gpt-5-nano with low reasoning effort"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "word1; word2; word3"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        result = extract_words("test phrase")
        
        # Verify the API call parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        
        assert call_args.kwargs['model'] == 'gpt-5-nano'
        assert call_args.kwargs['reasoning_effort'] == 'low'
        assert len(call_args.kwargs['messages']) == 2
        
        # Verify the result parsing
        assert result == ['word1', 'word2', 'word3']

    @patch('chatgpt.OpenAI')
    def test_get_definitions_api_key_passed(self, mock_openai):
        """Test that API key is passed to OpenAI client"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = WordList(words=[], context=None)
        mock_client.chat.completions.parse.return_value = mock_response
        mock_openai.return_value = mock_client
        
        with patch('chatgpt.OPENAI_API_KEY', 'test-api-key'):
            get_definitions("test")
        
        mock_openai.assert_called_with(api_key='test-api-key')

    @patch('chatgpt.OpenAI')
    def test_extract_words_api_key_passed(self, mock_openai):
        """Test that API key is passed to OpenAI client"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "test; words"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        with patch('chatgpt.OPENAI_API_KEY', 'test-api-key'):
            extract_words("test")
        
        mock_openai.assert_called_with(api_key='test-api-key')


if __name__ == "__main__":
    pytest.main([__file__])