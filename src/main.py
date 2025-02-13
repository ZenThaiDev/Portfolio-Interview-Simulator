import os
import sys
import logging
import asyncio

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gui.interview_gui import InterviewGUI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("interview_simulator.log"),  # Log to file
        logging.StreamHandler(sys.stdout),  # Log to console
    ],
)

# Configure asyncio policy for Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main():
    app = InterviewGUI()
    app.run()


if __name__ == "__main__":
    main()
