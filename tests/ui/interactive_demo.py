"""Interactive demo for CliChatbotUI.

Run with:
    uv run python tests/ui/interactive_demo.py
"""

from code_monkey.ui.impl.cli import CliChatbotUI
from code_monkey.ui.protocol import Command

ui = CliChatbotUI()

ui.system_message("Welcome to the CliChatbotUI demo.")
ui.system_message("Type anything to send a message. Type /clear to issue the clear command. Press Ctrl+C or Ctrl+D to quit.")

while True:
    try:
        event = ui.get_input("You: ")
    except SystemExit:
        ui.system_message("Goodbye!")
        break

    if event.command == Command.CLEAR:
        ui.system_message("Clear command received.")
    else:
        ui.assistant_message(f'Echo: "{event.text}"')
        ui.show_error(f"(demo error for input: {event.text!r})")
