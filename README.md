# Portfolio Interview Simulator

An intelligent interview simulation system that helps users practice university admission interviews by analyzing their portfolio and conducting realistic interview scenarios.

## Features

- **Portfolio Analysis**: Validates and analyzes user portfolios in various formats (PDF, TXT, DOCX, MD)
- **Interactive Interview Simulation**: Conducts realistic university admission interviews based on portfolio content
- **Multi-Language Support**: Supports multiple languages
- **Voice Input**: Enables voice responses with real-time transcription
- **Real-time Scoring**: Evaluates responses based on multiple criteria:
  - Clarity and Communication (0-25 points)
  - Relevance and Content (0-25 points)
  - Critical Thinking (0-25 points)
  - Overall Impact (0-25 points)
- **Modern GUI**: Features a clean, modern interface with dark/light mode support
- **Progress Tracking**: Shows interview progress and remaining questions
- **Constructive Feedback**: Provides detailed feedback for each response

## Requirements

- Python 3.x
- OpenAI API Key

## Installation

1. Clone the repository:

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your OpenAI API key:
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini  # or your preferred model
```

## Usage

1. Run the application:
```bash
python src/main.py
```

2. Select your portfolio file using the "Select Portfolio File" button
3. Choose your preferred language from the dropdown menu
4. Click "Start Interview" to begin the simulation
5. Respond to questions either by:
   - Typing in the text box
   - Using the voice input feature (click the microphone button)
6. View your scores and feedback throughout the interview
7. Receive a final evaluation at the end of the interview

## Project Structure

```
├── src/
│   ├── core/
│   │   ├── assistant_manager.py    # Manages OpenAI assistants
│   │   ├── audio_manager.py        # Handles voice input/output
│   │   ├── portfolio_manager.py    # Portfolio validation and analysis
│   │   ├── simulator.py            # Main interview simulation logic
│   │   ├── api_client.py          # OpenAI API client
│   │   └── interview_session.py    # Interview session management
│   ├── gui/
│   │   ├── interview_gui.py        # Main GUI window
│   │   ├── chat_components.py      # Chat interface components
│   │   ├── audio_components.py     # Audio control components
│   │   ├── progress_components.py  # Progress tracking components
│   │   └── language_components.py  # Language selection components
│   ├── config/
│   │   └── interview_config.py     # Interview configuration settings
│   └── main.py                     # Application entry point
├── requirements.txt                # Project dependencies
└── .env                           # Environment variables
```

## Configuration

The interview process can be configured through `src/config/interview_config.py`:
- Maximum questions: 5 (default)
- Minimum questions: 3 (default)
- Interview completion criteria
- Scoring parameters

## Dependencies

- openai: OpenAI API client
- customtkinter: Modern GUI toolkit
- python-dotenv: Environment variable management
- sounddevice: Audio recording
- soundfile: Audio file handling
- numpy: Numerical computations
- scipy: Scientific computing

## License

This project is licensed under the MIT License. See the LICENSE file for details.
