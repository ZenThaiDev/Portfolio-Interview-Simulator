import logging
import tempfile
from pathlib import Path
import sounddevice as sd
import soundfile as sf
import numpy as np
import asyncio
from .api_client import APIClient

class AudioManager:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)

    async def text_to_speech(self, text):
        try:
            speech_file_path = Path(tempfile.gettempdir()) / "temp_speech.mp3"
            response = await self.api_client._make_api_request_async(
                self.api_client.client.audio.speech.create,
                model="tts-1",
                voice="alloy",
                input=text
            )

            await asyncio.get_event_loop().run_in_executor(
                self.api_client.thread_pool,
                lambda: response.stream_to_file(str(speech_file_path))
            )

            if speech_file_path.exists():
                self.logger.debug(f"Created speech file at: {speech_file_path}")
                return str(speech_file_path)
            else:
                raise FileNotFoundError(
                    f"Failed to create speech file at: {speech_file_path}"
                )

        except Exception as e:
            self.logger.error(f"Error in text to speech conversion: {e}")
            raise

    async def play_audio(self, file_path):
        try:
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")

            data, samplerate = await asyncio.get_event_loop().run_in_executor(
                self.api_client.thread_pool, lambda: sf.read(file_path)
            )

            # Add small padding at start and end (0.5 seconds)
            padding_samples = int(0.5 * samplerate)
            if len(data.shape) == 1:  # Mono audio
                padding = np.zeros(padding_samples)
                data = np.concatenate([padding, data, padding])
            else:  # Stereo audio
                padding = np.zeros((padding_samples, data.shape[1]))
                data = np.concatenate([padding, data, padding])

            # Apply fade in and fade out
            fade_samples = int(0.05 * samplerate)  # 50ms fade
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)

            if len(data.shape) == 1:  # Mono audio
                data[:fade_samples] *= fade_in
                data[-fade_samples:] *= fade_out
            else:  # Stereo audio
                data[:fade_samples] *= fade_in[:, np.newaxis]
                data[-fade_samples:] *= fade_out[:, np.newaxis]

            # Play audio in a separate thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                self.api_client.thread_pool, lambda: (sd.play(data, samplerate), sd.wait())
            )

        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")
            raise

    async def record_audio(self, duration=None, stop_event=None, callback=None, language=None):
        try:
            # Audio recording parameters
            sample_rate = 44100
            channels = 1
            dtype = np.float32
            chunk_duration = 3.0  # Process in 3-second chunks for streaming
            chunk_samples = int(chunk_duration * sample_rate)

            # Create a temporary directory for chunks
            temp_dir = Path(tempfile.gettempdir()) / "audio_chunks"
            temp_dir.mkdir(exist_ok=True)

            # Initialize recording buffer and chunk management
            current_chunk = []
            chunk_counter = 0
            is_recording = True
            full_transcript = ""

            def audio_callback(indata, frames, time, status):
                if status:
                    self.logger.warning(f"Recording status: {status}")
                current_chunk.append(indata.copy())

            # Set up the recording stream
            stream = sd.InputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype=dtype,
                callback=audio_callback,
                blocksize=int(0.1 * sample_rate),  # 100ms blocks for responsiveness
            )

            async def process_chunk(chunk_data, chunk_num):
                try:
                    # Save chunk to temporary file
                    chunk_file = temp_dir / f"chunk_{chunk_num}.wav"
                    await asyncio.get_event_loop().run_in_executor(
                        self.api_client.thread_pool,
                        lambda: sf.write(chunk_file, chunk_data, sample_rate),
                    )

                    # Transcribe chunk
                    with open(chunk_file, "rb") as audio:
                        transcript = await asyncio.get_event_loop().run_in_executor(
                            self.api_client.thread_pool,
                            lambda: self.api_client.client.audio.transcriptions.create(
                                model="whisper-1", file=audio, response_format="text", language=language
                            ),
                        )

                    chunk_file.unlink()

                    return transcript.strip()
                except Exception as e:
                    self.logger.error(f"Error processing chunk {chunk_num}: {e}")
                    return ""

            with stream:
                self.logger.info("Started streaming recording...")
                while is_recording:
                    if stop_event and stop_event.is_set():
                        is_recording = False
                        break

                    # Wait for enough samples for a chunk
                    if len(current_chunk) * stream.blocksize >= chunk_samples:
                        # Process the current chunk
                        chunk_data = np.concatenate(current_chunk, axis=0)
                        current_chunk.clear()

                        # Process chunk and get transcription
                        transcript = await process_chunk(chunk_data, chunk_counter)

                        if transcript:
                            full_transcript += " " + transcript
                            # Call callback with interim results if provided
                            if callback:
                                await callback(full_transcript.strip())

                        chunk_counter += 1

                    await asyncio.sleep(0.1)

                # Process any remaining audio
                if current_chunk:
                    chunk_data = np.concatenate(current_chunk, axis=0)
                    transcript = await process_chunk(chunk_data, chunk_counter)
                    if transcript:
                        full_transcript += " " + transcript
                        if callback:
                            await callback(full_transcript.strip())

            return full_transcript.strip()

        except Exception as e:
            self.logger.error(f"Error in voice recording: {e}")
            raise
        finally:
            if "temp_dir" in locals() and temp_dir.exists():
                for chunk_file in temp_dir.glob("*.wav"):
                    chunk_file.unlink()
                temp_dir.rmdir() 
