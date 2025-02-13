import logging
import json
from .api_client import APIClient

class InterviewSession:
    def __init__(self, api_client: APIClient, assistant_manager, config):
        self.api_client = api_client
        self.assistant_manager = assistant_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.thread = None
        self.portfolio_data = None
        self.current_language = "en"  # Default language

    async def _process_response(self, messages):
        """Process response messages with retry logic"""
        try:
            response = messages.data[0].content[0].text.value
            response_data = json.loads(response)
            
            if response_data["data"]["message_type"] == "question":
                self.config.increment_question()
            elif response_data["data"]["message_type"] == "final_evaluation":
                self.config.is_completed = True
                
            return response
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            self.logger.error(f"Error processing response: {e}")
            raise

    async def start_interview(self):
        """Initialize the interview with portfolio content"""
        self.thread = await self.api_client._make_api_request_async(
            self.api_client.client.beta.threads.create
        )
        self.config.reset()

        try:
            message_content = {
                "type": "text",
                "text": f"""Start the interview. Here's the portfolio data: {self.portfolio_data}
                
                For first message, use "other", as stated in the instructions, to ask for the applicant's background and major they are applying for.

                Important Instructions:
                1. Ask only ONE question at a time
                2. Wait for my response before asking the next question
                3. You are encouraged to ask follow-up questions based on my answers to gain deeper insights (these do not count as a question). Please ensure that you frequently use this opportunity to clarify and explore my responses further.
                4. You must ask at least {self.config.min_questions} questions
                5. You cannot ask more than {self.config.max_questions} questions
                6. After each answer, decide if you want to:
                   - Ask a follow-up question (does not count as a question)
                   - Move to a new topic (start a new question by using "question" message type)
                   - Conclude the interview (only if min questions reached)
                7. Current question: {self.config.question_count}/{self.config.max_questions}
                8. Please communicate in {self.current_language} language
                """,
            }

            message = await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.messages.create,
                thread_id=self.thread.id,
                role="user",
                content=[message_content]
            )

            run = await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.runs.create,
                thread_id=self.thread.id,
                assistant_id=self.assistant_manager.interviewer.id,
            )

            await self.api_client._check_run_status(self.thread.id, run.id)

            messages = await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.messages.list,
                thread_id=self.thread.id
            )

            return await self._process_response(messages)

        except TimeoutError as e:
            self.logger.error(f"Interview start timed out: {e}")
            raise TimeoutError("The interview start process timed out. Please try again.")
        except Exception as e:
            self.logger.error(f"Error starting interview: {e}")
            raise

    async def submit_answer(self, answer):
        """Submit user's answer and get next question or feedback"""
        if self.config.is_completed:
            return "The interview has already been completed. Thank you for your participation."

        try:
            message = await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.messages.create,
                thread_id=self.thread.id,
                role="user",
                content=f"""My answer: {answer}

                Note: This is question #{self.config.question_count}. 
                - You can ask a follow-up question if needed
                - You can move to a new topic
                - You can conclude the interview if we've reached at least {self.config.min_questions} questions
                - Maximum questions allowed: {self.config.max_questions}
                - Questions remaining: {self.config.get_remaining_questions()}
                - Can conclude: {"Yes" if self.config.can_conclude() else "No"}
                - Should conclude: {"Yes" if self.config.should_conclude() else "No"}
                """
            )

            run = await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.runs.create,
                thread_id=self.thread.id,
                assistant_id=self.assistant_manager.interviewer.id,
            )

            await self.api_client._check_run_status(self.thread.id, run.id)

            messages = await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.messages.list,
                thread_id=self.thread.id
            )

            return await self._process_response(messages)

        except TimeoutError as e:
            self.logger.error(f"Answer submission timed out: {e}")
            raise TimeoutError("Processing your answer took too long. Please try submitting again.")
        except Exception as e:
            self.logger.error(f"Error submitting answer: {e}")
            raise

    def set_language(self, language_code):
        """Set the language for the interview"""
        self.current_language = language_code
        self.logger.info(f"Language set to: {language_code}")

    def set_portfolio_data(self, data):
        """Set the portfolio data for the interview"""
        self.portfolio_data = data 
