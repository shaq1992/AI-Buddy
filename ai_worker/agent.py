import os
import logging
from textwrap import dedent

from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI

# Assuming infra/google_doc_ai.py exists as per your tree
from infra.google_doc_ai import ocr_document

def get_gemini_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing!")
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        verbose=True,
        temperature=0.7,
        google_api_key=api_key
    )

def process_request(message: dict, job_logger: logging.LoggerAdapter) -> dict:
    """
    1. Extract Info
    2. OCR
    3. Run CrewAI
    4. Return Result
    """
    job_id = message.get("job_id")
    file_path = message.get("file_path")
    problem_statement = message.get("problem_statement")
    user_ideas = message.get("user_ideas")
    user_techstack = message.get("user_techstack")

    job_logger.info(f"Processing file: {file_path}")
    
    # 1. OCR Step
    try:
        resume_text = ocr_document(file_path)
        job_logger.info("OCR Extraction successful.")
    except Exception as e:
        job_logger.error(f"OCR Failed: {e}")
        return {
            "job_id": job_id,
            "status": "failed",
            "error": "OCR failed"
        }

    # 2. CrewAI Setup
    job_logger.info("Initializing Agents...")
    llm = get_gemini_llm()

    # Agent: Critic
    critic = Agent(
        role='Senior Tech Critic',
        goal='Validate user feasibility based on resume.',
        backstory="You are a strict technical lead who checks if a developer can actually build what they propose.",
        llm=llm,
        verbose=True
    )

    # Agent: Architect
    architect = Agent(
        role='Solutions Architect',
        goal='Design the technical implementation.',
        backstory="You build scalable system designs using the requested tech stack.",
        llm=llm,
        verbose=True
    )

    # Task: Critique
    task_critique = Task(
        description=dedent(f"""
            Context:
            - Resume: {resume_text[:3000]}
            - Problem: {problem_statement}
            - Proposal: {user_ideas}
            
            Analyze if the user has the skills to build this. Identify risks.
        """),
        expected_output="Bulleted list of technical risks.",
        agent=critic
    )

    # Task: Architecture
    task_arch = Task(
        description=dedent(f"""
            Create a build plan for the user's problem.
            Tech Stack: {user_techstack}
            Use the critique from the previous task.
        """),
        expected_output="Markdown technical report.",
        agent=architect
    )

    crew = Crew(
        agents=[critic, architect],
        tasks=[task_critique, task_arch],
        process=Process.sequential,
        verbose=True
    )

    job_logger.info("Kicking off Crew...")
    result = crew.kickoff()
    job_logger.info("Crew execution finished.")

    return {
        "job_id": job_id,
        "status": "completed",
        "result": str(result)
    }
