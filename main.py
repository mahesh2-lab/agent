from dotenv import load_dotenv
import os
from datetime import datetime
import json
import httpx
import re
from typing import Dict, List, Any
from livekit import agents, api
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    google,
    noise_cancellation,
)
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_GENAI_API_KEY"))


def analyze_transcript_content(transcript_data: Dict) -> Dict[str, Any]:
    """
    Analyze the transcript content to extract key insights about the interview.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction="""
                You are a highly skilled AI recruitment analyst trained in behavioral psychology, technical evaluation, and fair-hiring practices.
Your task is to analyze a structured interview transcript provided in JSON format and generate an objective, bias-free, and role-aligned hiring report in JSON format.
Use best practices in recruitment to evaluate the candidate’s communication, domain expertise, confidence, problem-solving ability, soft skills, and technical depth.
Do not penalize for language fluency or grammar if the candidate demonstrates strong technical understanding or clear problem-solving ability.

🔍 Input JSON Format:
{
  "items": [ 
    { "id": "...", "type": "message", "role": "assistant" | "user", "content": ["..."], "interrupted": true | false } 
  ],
  "roleProfile": {
    "title": "Frontend Developer",
    "requiredSkills": ["JavaScript", "HTML", "CSS", "React"],
    "softSkills": ["Communication", "Teamwork", "Problem Solving"]
  },
  "candidateMeta": {
    "name": "Optional",
    "interviewDate": "Optional",
    "interviewRound": 1,
    "previousScores": {
      "communicationSkills": 6,
      "domainKnowledge": 5
    }
  }
}
📤 Output JSON Format:
{
  "candidateOverview": {
    "candidateName": "",
    "roleApplied": "",
    "interviewDate": "",
    "interviewRound": 1,
    "communicationSkills": 0,
    "confidenceLevel": 0,
    "domainKnowledge": 0,
    "problemSolvingSkills": 0,
    "culturalFit": ""
  },
  "interviewStatistics": {
    "totalQuestionsAsked": 0,
    "totalCandidateResponses": 0,
    "estimatedDurationMinutes": 0,
    "candidateTalkRatioPercent": 0,
    "technicalToBehavioralRatio": "",
    "keywordsMentioned": [],
    "positiveIndicators": [],
    "negativeIndicators": []
  },
  "behavioralAnalysis": {
    "leadership": "",
    "communicationClarity": "",
    "adaptability": "",
    "teamCollaboration": "",
    "emotionalIntelligence": ""
  },
  "technicalEvaluation": {
    "mainChallengesDiscussed": [],
    "solutionsProposed": [],
    "technicalDepth": "",
    "alignmentWithRoleRequirements": "",
    "toolsOrTechnologiesMentioned": []
  },
  "biasCheck": {
    "grammarFluencyIssues": false,
    "didAffectScoring": false,
    "notes": ""
  },
  "hiringRecommendation": {
    "status": "",
    "reasoning": ""
  },
  "improvementSuggestions": [
    "",
    ""
  ],
  "sentimentToneAnalysis": {
    "overallSentiment": "",
    "toneBreakdown": {
      "confidence": "",
      "hesitation": "",
      "enthusiasm": "",
      "engagement": ""
    },
    "languageObservations": []
  },
  "overallSuitabilityScore": {
    "combinedScoreOutOf10": 0,
    "comparisonToPreviousRounds": "",
    "finalVerdict": ""
  }
}
            
            """
        ),
        contents=json.dumps(transcript_data),
    )

    try:
        # Remove any code block markers (e.g., ```json ... ```) before parsing
        cleaned_response = re.sub(
            r"```(?:json)?(.*?)```", r"\1", response.text.strip(), flags=re.DOTALL)
        parsedData = json.loads(cleaned_response)

    except Exception as e:
        return {
            "error": f"Failed to parse model response as JSON: {e}",
            "raw_response": response.text.strip()
        }

    if not parsedData:
        return {
            "error": "No analysis data returned from the model."
        }

    return {
        "room_name": transcript_data.get("room_name"),
        "analysis": parsedData,
        "status": "completed"
    }


async def send_analysis_to_frontend(analysis: Dict[str, Any], room_name: str) -> None:
    """Send analysis results to the frontend via the backend API."""
    try:
        server_url = "https://18.232.134.110"
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                f"{server_url}/api/analysis/receive",
                json={
                    "room_name": room_name,
                    "analysis": analysis,
                    "status": "completed"
                }
            )
            if response.status_code == 200:
                print("📤 Analysis sent to frontend successfully")
            else:
                print(f"⚠️ Failed to send analysis: {response.status_code}")
    except (httpx.TimeoutException, httpx.RequestError) as e:
        print(f"⚠️ Error sending analysis to frontend: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error sending analysis to frontend: {e}")


async def process_transcript_post_interview(
    transcript_data: Dict,
    room_name: str,
    candidate_details: str,
    job_description: str
) -> Dict[str, Any]:
    """
    Main function to process transcript after interview completion.
    """

    print(f"🔄 transcript {transcript_data}")

    # Analyze the transcript
    analysis = analyze_transcript_content(transcript_data)

    print(analysis)

    # Add original context to analysis
    analysis['context'] = {
        'candidate_details': candidate_details,
        'job_description': job_description,
        'room_name': room_name
    }

    # Send analysis to frontend
    await send_analysis_to_frontend(analysis, room_name)

    return analysis


def generate_ai_interviewer_prompt_simplified(
    candidate_details_text: str,
    job_description: str
) -> str:
    with open("prompt.txt", "r") as file:
        prompt_template = file.read()

    prompt = prompt_template.format(
        candidate_details_text=candidate_details_text,
        job_description=job_description
    )

    return prompt.strip()


class Assistant(Agent):
    def __init__(self, candidate_details: str, job_description: str) -> None:
        generated_prompt = generate_ai_interviewer_prompt_simplified(
            candidate_details_text=candidate_details,
            job_description=job_description
        )
        super().__init__(instructions=generated_prompt)


async def entrypoint(ctx: agents.JobContext):
    print(f"🚀 Starting agent for room: {ctx.room.name}")

    # Accept the job first to avoid timeout issues
    await ctx.connect()
    print("✅ Job accepted and connected to room")

    # Now fetch room data with proper timeout handling
    server_url = "https://18.232.134.110"  # Replace with your server's actual URL
    candidate_details_text = ""
    job_description_text = ""

    try:
        print("🔄 Fetching room data from backend...")
        async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
            response = await client.get(f"{server_url}/api/room/{ctx.room.name}")
            response.raise_for_status()  # Raise an exception for HTTP errors
            room_data = response.json().get("analysisData", {})

            print(f"✅ Retrieved room data: {room_data}")  # Debugging line

            candidate_details_text = room_data.get("candidateDetails", "")
            job_description_text = room_data.get("jobDescription", "")

    except (httpx.TimeoutException, httpx.RequestError) as e:
        print(f"⚠️ Error fetching room data: {e}")
        # Provide fallback data or graceful degradation
        candidate_details_text = "General candidate for technical interview"
        job_description_text = "Technical role requiring problem-solving and domain expertise"

    if not candidate_details_text or not job_description_text:
        print("⚠️ Warning: Using fallback candidate details or job description.")
        candidate_details_text = candidate_details_text or "General candidate for technical interview"
        job_description_text = job_description_text or "Technical role requiring problem-solving and domain expertise"

    async def write_transcript():
        try:
            current_date = datetime.now().strftime("%Y%m%d_%H%M%S")

            # This example writes to the temporary directory, but you can save to any location
            # Ensure the directory exists before writing the file
            # Save transcript only if session has history
            if session.history and session.history.to_dict():
                os.makedirs("./tmp", exist_ok=True)

                # Save original transcript
                transcript_data = session.history.to_dict()
                filename = f"./tmp/transcript_{ctx.room.name}_{current_date}.json"
                with open(filename, 'w') as f:
                    json.dump(transcript_data, f, indent=2)
                print(f"📄 Transcript for {ctx.room.name} saved to {filename}")

                # Process the transcript for analysis
                await process_transcript_post_interview(
                    transcript_data,
                    ctx.room.name,
                    candidate_details_text,
                    job_description_text
                )

            else:
                print("⚠️ No transcript data to save.")

        except Exception as e:
            print(f"⚠️ Error in write_transcript: {e}")
            # Don't let transcript saving errors crash the shutdown process
            return

    print("🤖 Creating AI agent session...")
    session = AgentSession(
        llm=google.beta.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",
            voice="Charon",
            temperature=0.8,
        ),
    )

    print("🔄 Starting agent session...")
    await session.start(
        room=ctx.room,
        agent=Assistant(
            candidate_details=candidate_details_text,
            job_description=job_description_text
        ),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
            close_on_disconnect=False,
        ),
    )

    ctx.add_shutdown_callback(write_transcript)
    print("✅ Agent session started successfully")

    await session.generate_reply(
        instructions="Please conduct a technical interview with the candidate based on the provided system prompt and job description. Focus on assessing their deep technical knowledge, problem-solving skills, and practical application abilities relevant to the candidate's target role and the job description provided."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
