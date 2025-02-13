import logging
import json
import time
import hashlib
import asyncio
from pathlib import Path
from .api_client import APIClient

class PortfolioManager:
    def __init__(self, api_client: APIClient, assistant_manager):
        self.api_client = api_client
        self.assistant_manager = assistant_manager
        self.logger = logging.getLogger(__name__)
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.portfolio_cache = {}
        self._load_cache()

    def _load_cache(self):
        cache_file = self.cache_dir / "portfolio_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    self.portfolio_cache = json.load(f)
                self.logger.debug(
                    f"Loaded {len(self.portfolio_cache)} cached portfolios"
                )
            except Exception as e:
                self.logger.error(f"Error loading cache: {e}")
                self.portfolio_cache = {}

    def _save_cache(self):
        cache_file = self.cache_dir / "portfolio_cache.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(self.portfolio_cache, f)
            self.logger.debug("Portfolio cache saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving cache: {e}")

    def _calculate_file_hash(self, file_path):
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating file hash: {e}")
            return None

    async def validate_portfolio(self, file_path):
        """Validate portfolio content before starting interview"""
        self.logger.info("Starting portfolio validation")

        file_hash = self._calculate_file_hash(file_path)
        if not file_hash:
            return {
                "valid": False,
                "message": "Error calculating file hash",
                "data": None,
            }

        if file_hash in self.portfolio_cache:
            cached_data = self.portfolio_cache[file_hash]
            self.logger.info("Using cached portfolio validation")
            # Update last accessed time
            cached_data["last_accessed"] = time.time()
            self._save_cache()
            return cached_data["validation_result"]

        # Cache miss, proceed with validation
        thread = await self.api_client._make_api_request_async(
            self.api_client.client.beta.threads.create
        )
        self.logger.debug(f"Created validation thread: {thread.id}")

        try:
            file_upload = await self.api_client._make_api_request_async(
                self.api_client.client.files.create,
                file=open(file_path, "rb"),
                purpose="assistants"
            )
            self.logger.debug(f"File uploaded successfully with ID: {file_upload.id}")

            await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.messages.create,
                thread_id=thread.id,
                role="user",
                content=[
                    {
                        "type": "text",
                        "text": "Please validate this portfolio file and analyze its contents.",
                    }
                ],
                attachments=[
                    {
                        "file_id": file_upload.id,
                        "tools": [
                            {"type": "file_search"},
                            {"type": "code_interpreter"},
                        ],
                    }
                ],
            )

            run = await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.runs.create,
                thread_id=thread.id,
                assistant_id=self.assistant_manager.validator.id,
            )

            await self.api_client._check_run_status(thread.id, run.id)

            messages = await self.api_client._make_api_request_async(
                self.api_client.client.beta.threads.messages.list,
                thread_id=thread.id
            )

            try:
                validation_result = json.loads(messages.data[0].content[0].text.value)
                self.logger.info("Portfolio validation completed successfully")

                if validation_result["valid"]:
                    self.portfolio_cache[file_hash] = {
                        "validation_result": validation_result,
                        "file_path": str(file_path),
                        "last_accessed": time.time(),
                    }
                    self._save_cache()

                await asyncio.get_event_loop().run_in_executor(
                    self.api_client.thread_pool,
                    lambda: self.api_client.client.files.delete(file_upload.id),
                )

                return validation_result
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse validation response: {e}")
                raw_response = messages.data[0].content[0].text.value
                return {
                    "valid": False,
                    "message": f"Error parsing validation response. Raw response: {raw_response[:200]}...",
                    "data": None,
                }

        except Exception as e:
            self.logger.error(f"Error during portfolio validation: {e}")
            return {
                "valid": False,
                "message": f"Error during validation: {str(e)}",
                "data": None,
            }

    def cleanup(self):
        """Clean old cache entries (older than 30 days)"""
        current_time = time.time()
        max_age = 30 * 24 * 60 * 60  # 30 days in seconds
        self.portfolio_cache = {
            k: v
            for k, v in self.portfolio_cache.items()
            if current_time - v["last_accessed"] < max_age
        }
        self._save_cache()
