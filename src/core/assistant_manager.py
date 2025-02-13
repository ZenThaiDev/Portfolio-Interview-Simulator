import os
import json
import logging
import openai
from dotenv import load_dotenv

load_dotenv()

class AssistantManager:
    def __init__(self):
        self.config_file = "assistants_config.json"
        self.client = openai.Client()
        self.interviewer = None
        self.validator = None
        self.logger = logging.getLogger(__name__)
        self.default_model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.load_or_create_assistants()

    def load_or_create_assistants(self):
        self.logger.info("Loading or creating assistants...")

        # Define configurations
        configs = {
            "interviewer": {
                "name": "Interview Simulator",
                "instructions": """As a university admission interviewer, your responsibilities include:
                1. Begin by greeting the applicant and inquiring about their background and the major they are applying for. Use the "other" message type for the initial message.
                2. Review the applicant's portfolio and pose questions regarding their experiences, achievements, and aspirations.
                3. Ensure questions are relevant to their experiences and aspirations.
                4. Evaluate each response based on these criteria:
                   - Clarity and Communication (0-25 points)
                   - Relevance and Content (0-25 points)
                   - Critical Thinking (0-25 points)
                   - Overall Impact (0-25 points)
                5. Provide constructive feedback for each response.
                6. Show judgement result if the applicant is accepted or rejected.

                Difficulty level: Realistic and challenging, challenge back with a follow up question about the previous answer or the knowledge of the applicant.
                For example but not limited to:
                - If the applicant says they are a good leader, you can ask them to explain a time they led a team and how they contributed to the team.
                - If the applicant says they used a specific technology, you can ask them to explain how they used it and what they learned from it.
                
                Keep questions concise and focused primarily on the portfolio content, with some general university admission inquiries. The interview will carry more weight in scoring than the portfolio itself. Encourage critical thinking and actively seek opportunities for mini follow-ups to delve deeper into the applicant's responses. Conclude the interview once sufficient information has been gathered or the maximum number of questions has been reached. Track scores throughout the interview and deliver a final evaluation.

                Message types include:
                - question: Pose a unique question that completely changes the topic and is no longer related to the previous one. Use this only for new questions.
                - follow_up: Request additional context or clarification on a previous answer or ask for more information related to the same topic. This does not count as a question and should be used frequently to enhance understanding, especially for similar or continued questions.
                - final_eval: Provide a final evaluation.
                - other: Ask an unrelated question or make a statement. This does not count as a question.

                IMPORTANT RULES FOR MESSAGE TYPES:
                1. The first message MUST be of type "other" - use this for the initial greeting and background inquiry.
                2. Use "question" ONLY for new, unique questions that completely change the topic.
                3. Use "follow_up" for clarifications, additional context, or similar inquiries. Encourage frequent use of this type to ensure clarity, particularly for similar or related inquiries.
                4. Use "other" for general statements, greetings, or transitions between topics.
                5. Use "final_eval" only for the final evaluation message.

                For repeated questions, use the "follow_up" message type. For questions unrelated to the portfolio or admission requirements, use the "other" message type. Use "other" for responses not related to the interview or for repeated statements.
                If the user goes off topic or doesn't answer the question and you have to ask again, use the "follow_up" message type.
                Don't use message type "question" after the user goes off topic or didn't answer the question. Use "other" or "follow_up" instead.
                Avoid using "question" message type if the user hasn't answered the previous question yet.
                    
                IMPORTANT: All responses must adhere to the specified JSON format below.""",
                "model": self.default_model,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "interview_simulator",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "scores": {
                                    "type": "object",
                                    "properties": {
                                        "clarity_and_communication": {
                                            "type": "number",
                                            "description": "Score for clarity and communication, ranging from 0 to 25.",
                                        },
                                        "relevance_and_content": {
                                            "type": "number",
                                            "description": "Score for relevance and content, ranging from 0 to 25.",
                                        },
                                        "critical_thinking": {
                                            "type": "number",
                                            "description": "Score for critical thinking, ranging from 0 to 25.",
                                        },
                                        "overall_impact": {
                                            "type": "number",
                                            "description": "Score for overall impact, ranging from 0 to 25.",
                                        },
                                    },
                                    "required": [
                                        "clarity_and_communication",
                                        "relevance_and_content",
                                        "critical_thinking",
                                        "overall_impact",
                                    ],
                                    "additionalProperties": False,
                                },
                                "data": {
                                    "type": "object",
                                    "properties": {
                                        "message": {
                                            "type": "string",
                                            "description": "The content of the message",
                                        },
                                        "message_type": {
                                            "type": "string",
                                            "enum": [
                                                "question",
                                                "follow_up",
                                                "final_eval",
                                                "others",
                                            ],
                                            "description": "The type of message being sent",
                                        },
                                    },
                                    "required": ["message", "message_type"],
                                    "additionalProperties": False,
                                },
                                "final_evaluation": {
                                    "type": "string",
                                    "description": "Overall evaluation of the applicant's performance during the interview.",
                                },
                            },
                            "required": ["scores", "data", "final_evaluation"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            },
            "validator": {
                "name": "Portfolio Validator",
                "instructions": """You are a portfolio validator. Your role is to:
                1. Check if the provided portfolio content is readable and contains meaningful information
                2. Verify if it contains essential elements like education, achievements, or experiences
                3. Provide validation results in the specified JSON format
                
                Don't strict about validation, just focus and be strict if the file is not readable or doesn't contain any meaningful information.
                You can process various file formats including PDFs. When analyzing PDFs, look for text content,
                sections, and structure to validate the portfolio.
                
                IMPORTANT: Always respond with the exact JSON format specified above. The response must be valid JSON.""",
                "model": self.default_model,
                "tools": [{"type": "file_search"}, {"type": "code_interpreter"}],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "portfolio_validation",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "valid": {
                                    "type": "boolean",
                                    "description": "Whether the portfolio is valid and contains sufficient information.",
                                },
                                "message": {
                                    "type": "string",
                                    "description": "Explanation or error message about the validation result.",
                                },
                                "data": {
                                    "type": "string",
                                    "description": "An object containing the actual data of the response. Ideally a JSON object.",
                                },
                            },
                            "required": ["valid", "message", "data"],
                            "additionalProperties": False,
                        },
                    },
                },
            },
        }

        # Load existing IDs or create new assistants
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    existing_ids = json.load(f)
                    self.logger.debug("Attempting to update existing assistants")
                    self.interviewer = self.client.beta.assistants.update(
                        assistant_id=existing_ids["interviewer_id"],
                        **configs["interviewer"],
                    )
                    self.logger.debug(
                        f"Updated interviewer assistant: {self.interviewer.id}"
                    )
                    self.validator = self.client.beta.assistants.update(
                        assistant_id=existing_ids["validator_id"],
                        **configs["validator"],
                    )
                    self.logger.debug(
                        f"Updated validator assistant: {self.validator.id}"
                    )
                    return
        except Exception as e:
            self.logger.warning(f"Failed to update existing assistants: {e}")

        # Create new if update failed or no existing config
        self.logger.info("Creating new assistants...")
        self.interviewer = self.client.beta.assistants.create(**configs["interviewer"])
        self.validator = self.client.beta.assistants.create(**configs["validator"])

        # Save new IDs
        with open(self.config_file, "w") as f:
            json.dump(
                {
                    "interviewer_id": self.interviewer.id,
                    "validator_id": self.validator.id,
                },
                f,
            )
