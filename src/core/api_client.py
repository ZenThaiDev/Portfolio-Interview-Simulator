import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import openai

class APIClient:
    def __init__(self):
        self.client = openai.Client()
        self.logger = logging.getLogger(__name__)
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self._run_status_check = True
        self.max_retries = 2
        self.base_timeout = 30.0
        self.max_run_retries = 2
        self.run_timeout = 30.0

    def get_client(self):
        return self.client

    async def _check_run_status(self, thread_id, run_id, callback=None):
        """Asynchronously check run status with timeout"""
        start_time = asyncio.get_event_loop().time()
        retry_count = 0
        
        try:
            while self._run_status_check:
                try:
                    run = await self._make_api_request_async(
                        self.client.beta.threads.runs.retrieve,
                        thread_id=thread_id,
                        run_id=run_id
                    )
                    
                    # Check if run failed or expired
                    if run.status in ["failed", "expired", "cancelled"]:
                        self.logger.error(f"Run failed with status: {run.status}")
                        if retry_count < self.max_run_retries:
                            retry_count += 1
                            self.logger.info(f"Retrying run (attempt {retry_count}/{self.max_run_retries})")
                            # Create new run
                            run = await self._make_api_request_async(
                                self.client.beta.threads.runs.create,
                                thread_id=thread_id,
                                assistant_id=run.assistant_id
                            )
                            run_id = run.id  # Update run_id for the new run
                            continue
                        raise Exception(f"Run failed after {self.max_run_retries} attempts")
                    
                    # Check if run completed
                    if run.status not in ["queued", "in_progress"]:
                        if callback:
                            await callback(run)
                        return run
                    
                    # Check for timeout
                    elapsed_time = asyncio.get_event_loop().time() - start_time
                    if elapsed_time > self.run_timeout:
                        if retry_count < self.max_run_retries:
                            retry_count += 1
                            self.logger.warning(f"Run timed out, retrying (attempt {retry_count}/{self.max_run_retries})")
                            # Cancel current run
                            try:
                                await self._make_api_request_async(
                                    self.client.beta.threads.runs.cancel,
                                    thread_id=thread_id,
                                    run_id=run_id
                                )
                            except:
                                pass
                            # Create new run
                            run = await self._make_api_request_async(
                                self.client.beta.threads.runs.create,
                                thread_id=thread_id,
                                assistant_id=run.assistant_id
                            )
                            run_id = run.id  # Update run_id for the new run
                            start_time = asyncio.get_event_loop().time()  # Reset timer
                            continue
                        raise TimeoutError(f"Run timed out after {self.run_timeout} seconds and {self.max_run_retries} retries")
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    if not isinstance(e, TimeoutError):
                        self.logger.error(f"Error checking run status: {e}")
                    raise
                    
        except Exception as e:
            self.logger.error(f"Final error in run status check: {e}")
            raise

    def _run_in_thread(self, func, *args, **kwargs):
        return self.thread_pool.submit(func, *args, **kwargs)

    def _make_api_request(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    async def _make_api_request_async(self, func, *args, **kwargs):
        last_error = None
        for retry in range(self.max_retries):
            try:
                # Increase timeout with each retry
                timeout = self.base_timeout * (retry + 1)
                self.logger.debug(f"Attempt {retry + 1}/{self.max_retries} with timeout {timeout}s")
                
                return await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        self.thread_pool,
                        lambda: self._make_api_request(func, *args, **kwargs)
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError as e:
                last_error = e
                self.logger.warning(f"API request timed out after {timeout} seconds (attempt {retry + 1}/{self.max_retries})")
                if retry < self.max_retries - 1:
                    await asyncio.sleep(1 * (retry + 1))  # Exponential backoff
                    continue
                self.logger.error("All retry attempts failed due to timeout")
                raise TimeoutError(f"API request failed after {self.max_retries} attempts")
            except Exception as e:
                last_error = e
                self.logger.warning(f"API request failed: {str(e)} (attempt {retry + 1}/{self.max_retries})")
                if retry < self.max_retries - 1:
                    await asyncio.sleep(1 * (retry + 1))  # Exponential backoff
                    continue
                self.logger.error(f"All retry attempts failed: {str(last_error)}")
                raise

    def cleanup(self):
        self._run_status_check = False
        self.thread_pool.shutdown(wait=True) 
