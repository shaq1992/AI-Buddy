import os
import logging
from typing import List, AsyncGenerator, Any
from google import genai
from google.genai import types
from agent_framework import ChatClientProtocol, ChatMessage

logger = logging.getLogger(__name__)

class GeminiChatClient(ChatClientProtocol):
    """
    A Custom Adapter that allows the Microsoft Agent Framework to talk to Google Gemini.
    """
    def __init__(self, model_id: str = "gemini-2.0-flash"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = model_id

    async def get_response(self, messages: List[ChatMessage]) -> Any:
        """
        Non-streaming response handler.
        Converts Framework Messages -> Gemini Content -> Framework Response
        """
        gemini_contents = self._convert_to_gemini_format(messages)
        
        try:
            # 1. Real Call to Google Gemini
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=gemini_contents
            )
            
            # 2. Wrap result in a safe adapter object
            return self._wrap_response(response.text)

        except Exception as e:
            logger.error(f"Gemini API Call Failed: {e}")
            raise

    async def get_streaming_response(self, messages: List[ChatMessage]) -> AsyncGenerator[Any, None]:
        """
        Streaming is required by the ChatAgent protocol.
        """
        gemini_contents = self._convert_to_gemini_format(messages)
        
        # Simple streaming implementation
        response_stream = self.client.models.generate_content_stream(
            model=self.model_id,
            contents=gemini_contents
        )
        
        for chunk in response_stream:
            # Yield chunks in a format the framework expects
            yield self._wrap_delta(chunk.text)

    def _convert_to_gemini_format(self, messages: List[ChatMessage]) -> List[types.Content]:
        """
        Maps generic Agent Framework messages (System, User, Assistant) to Gemini Content objects.
        """
        formatted_history = []
        
        for msg in messages:
            # FIX 1: Handle Enum vs String for Role safely
            # The framework uses Enums (Role.USER), but simpler tests might use strings.
            if hasattr(msg.role, 'value'):
                role = msg.role.value.lower()
            else:
                role = str(msg.role).lower()
            
            # Map roles to Gemini format
            if "system" in role:
                # Gemini 1.5/2.0 supports system instructions, but mixing them in history 
                # often requires treating them as User prompts with a prefix for simplicity.
                formatted_history.append(types.Content(
                    role="user",
                    parts=[types.Part(text=f"SYSTEM INSTRUCTION: {msg.content}")]
                ))
            elif "user" in role:
                formatted_history.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg.content)]
                ))
            elif "assistant" in role or "model" in role:
                formatted_history.append(types.Content(
                    role="model",
                    parts=[types.Part(text=msg.content)]
                ))
                
        return formatted_history

    def _wrap_response(self, text: str):
        """
        Wraps text in a mock object that mimics an OpenAI-style response object 
        expected by the Agent Framework.
        """
        return MockResponse(text)

    def _wrap_delta(self, text: str):
        return MockStreamDelta(text)

# --- SAFE MOCK CLASSES ---
# We define our own simple classes to guarantee attributes like .content exist.
# We do NOT use the library's ChatMessage class here to avoid schema validation errors.

class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]

class MockChoice:
    def __init__(self, content):
        # FIX 2: Use SimpleMessage instead of library ChatMessage
        self.message = SimpleMessage(role="assistant", content=content)

class SimpleMessage:
    """A simple data holder that guarantees .content and .role exist."""
    def __init__(self, role, content):
        self.role = role
        self.content = content

class MockStreamDelta:
    def __init__(self, content):
        self.choices = [MockDeltaChoice(content)]

class MockDeltaChoice:
    def __init__(self, content):
        self.delta = MockDeltaContent(content)

class MockDeltaContent:
    def __init__(self, content):
        self.content = content
