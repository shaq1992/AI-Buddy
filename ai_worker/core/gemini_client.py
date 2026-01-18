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
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=gemini_contents
            )
            
            # Convert Gemini response back to a simplistic Framework-compatible format
            # The framework expects an object that has a 'message' or 'choices' attribute depending on usage.
            # For our simple agent, returning a standard ChatMessage is usually sufficient if the agent handles it.
            # However, strictly speaking, we return a structure the Agent expects.
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
            # Yield chunks in a format the framework expects (Simulated Delta)
            yield self._wrap_delta(chunk.text)

    def _convert_to_gemini_format(self, messages: List[ChatMessage]) -> List[types.Content]:
        """
        Maps generic Agent Framework messages (System, User, Assistant) to Gemini Content objects.
        """
        formatted_history = []
        
        for msg in messages:
            role = msg.role.lower()
            
            # Map 'system' to 'user' with a distinct instruction for Gemini models 
            # (unless using a model that supports strict system instructions, but this is safer)
            if role == "system":
                # We can prepend system instructions to the first user message or send as model config.
                # For simplicity here, we treat it as a "developer" instruction if supported, or just User.
                # Gemini 1.5+ supports system_instruction at client level, but for per-request context:
                formatted_history.append(types.Content(
                    role="user",
                    parts=[types.Part(text=f"SYSTEM INSTRUCTION: {msg.content}")]
                ))
            elif role == "user":
                formatted_history.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg.content)]
                ))
            elif role == "assistant":
                formatted_history.append(types.Content(
                    role="model",
                    parts=[types.Part(text=msg.content)]
                ))
                
        return formatted_history

    def _wrap_response(self, text: str):
        """
        Wraps text in a mock object that mimics an OpenAI-style response object 
        if the framework strictly checks attributes, or just returns a ChatMessage.
        """
        # The simplest valid return for the basic ChatAgent is often just a ChatMessage 
        # but wrapped in a response envelope.
        return MockResponse(text)

    def _wrap_delta(self, text: str):
        return MockStreamDelta(text)

# Helper Mocks to satisfy Framework Type Checks
class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]

class MockChoice:
    def __init__(self, content):
        self.message = ChatMessage(role="assistant", content=content)

class MockStreamDelta:
    def __init__(self, content):
        self.choices = [MockDeltaChoice(content)]

class MockDeltaChoice:
    def __init__(self, content):
        self.delta = MockDeltaContent(content)

class MockDeltaContent:
    def __init__(self, content):
        self.content = content