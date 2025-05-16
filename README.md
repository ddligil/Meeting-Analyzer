# Meeting-Analyzer
Meeting Analyzer is a tkinter-based voice recording tool powered by LLMs. It lets users manually start and stop recording during a meeting, so only important parts are captured. You can pause at any time, skip irrelevant content, and resume recording seamlessly.

At the end of the session:

All .wav segments are merged into a single audio file
The audio is transcribed using OpenAI Whisper
A GPT-4-based intelligent agent processes the transcript to extract structured insights such as:
👥 Participants
📝 Decisions made
💡 Shared information
❗ Mentioned problems
📆 Next meeting schedule or agenda
The final output is returned in JSON format, ready for use in other systems like Airtable, Notion, or internal documentation tools.

This tool makes it easy to skip unnecessary parts, focus on key moments, and get an automatic summary of what truly matters in your meetings.
