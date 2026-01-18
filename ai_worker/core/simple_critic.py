import logging
from agent_framework import ChatAgent, ChatMessage
from .gemini_client import GeminiChatClient

logger = logging.getLogger(__name__)

# 1. Define the Persona
CRITIC_SYSTEM_PROMPT = """
You are a Senior Principal Engineer and Technical Critic. 
Your goal is to provide unbiased, constructive, and rigorous criticism of technical approaches.

You will be given:
1. A Problem Statement
2. The User's Current Ideas/Approach
3. The User's Tech Stack
4. The User's Resume (Context on their skills)

Your Output must be in Markdown and strictly follow this structure:
## 1. Executive Summary
A 2-sentence summary of whether the user's approach is viable.

## 2. Critical Analysis
- **Strengths:** What did the user get right?
- **Weaknesses:** Identify bottlenecks, scalability issues, or anti-patterns.
- **Skill Gap Analysis:** Based on their resume, are they trying to use tools they don't know?

## 3. The "Devil's Advocate"
Propose one major counter-argument or edge case that breaks their current idea.
"""

async def analyze_request(
    problem: str, 
    user_ideas: str, 
    user_techstack: str, 
    resume_text: str
) -> str:
    """
    Orchestrates the Critic Agent to review the user's submission.
    """
    try:
        # 2. Initialize the Client (The Brain)
        client = GeminiChatClient(model_id="gemini-2.0-flash-exp")

        # 3. Initialize the Agent (The Persona)
        critic_agent = ChatAgent(
            name="SeniorCritic",
            description="A harsh but fair technical critic.",
            system_message=CRITIC_SYSTEM_PROMPT,
            chat_client=client
        )

        # 4. Construct the User Payload
        user_message_content = f"""
        --- INCOMING REQUEST ---
        **Problem Statement:** {problem}
        
        **User Ideas:** {user_ideas}
        
        **User Tech Stack:** {user_techstack}
        
        **Resume Context:** {resume_text[:10000]} # Truncate to avoid context limits if resume is huge
        ------------------------
        Please critique this approach.
        """

        # 5. Execute the Chat
        # Note: The framework usually uses 'process' or 'chat'. 
        # We send a message history containing the User's prompt.
        messages = [
            ChatMessage(role="user", content=user_message_content)
        ]
        
        logger.info("Critic Agent: Analyzing request...")
        response = await client.get_response(messages)
        
        # Extract the text content from our MockResponse wrapper
        # (Assuming choices[0].message.content structure from our adapter)
        critique_text = response.choices[0].message.content
        
        return critique_text

    except Exception as e:
        logger.error(f"Critic Agent failed: {e}")
        return f"Error generating critique: {str(e)}"