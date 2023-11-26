import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QStyleFactory
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPalette, QColor, QTextCursor, QIcon
from bs4 import BeautifulSoup
import requests
import openai
import time

# Load API key from a text file
with open('API-KEY.txt', 'r') as file:
    api_key = file.read().strip()

# Set your OpenAI GPT-3.5 API key
openai.api_key = api_key

# Set a user agent to avoid 403 errors
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

# Initialize an empty list to store extracted content
content_list = []

class GPTApp(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Set a dark theme
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(dark_palette)

        self.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: none }")

        # Set the window icon
        self.setWindowIcon(QIcon('wikipedia_wiki_2108.png'))  # Replace 'path/to/your/icon.png' with the actual path to your icon


        self.url_label = QLabel("Enter the website URL:")
        self.url_label.setStyleSheet("color: white;")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setStyleSheet("color: white; background-color: #424242; border: none; padding: 5px; font-size: 11px; border-radius: 3px;")
        self.url_input.setMinimumWidth(300)
        self.url_input.setMinimumHeight(30)

        self.question_label = QLabel("Prompt:")
        self.question_label.setStyleSheet("color: white;")
        self.question_input = QTextEdit()
        self.question_input.setPlaceholderText("What do you want to know?")
        self.question_input.setStyleSheet("color: white; background-color: #424242; border: none; padding: 5px; font-size: 12px; border-radius: 3px;")
        self.question_input.setMinimumWidth(300)
        self.question_input.setMaximumHeight(60)  # Reduced height
        self.question_input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Hide vertical scrollbar

        self.ask_btn = QPushButton("Ask GPT-3.5")
        self.ask_btn.setStyleSheet("color: white; background-color: #424242; border: 1px solid #5c5c5c; padding: 5px; margin-top: 5px; border-radius: 3px")
        self.gpt_response_output = QTextEdit()
        self.gpt_response_output.setReadOnly(True)  # Set the output box to read-only
        self.gpt_response_output.setMinimumWidth(300)
        self.gpt_response_output.setMinimumHeight(100)  # Reduced height
        self.gpt_response_output.setStyleSheet("color: white; background-color: #424242; border: 1px solid #5c5c5c; border-radius: 3px; padding: 5px; selection-color: white; selection-background-color: #2a82da; font-size: 13px;")

        self.ask_btn.clicked.connect(self.ask_gpt)

        layout.addWidget(self.url_label)
        layout.addWidget(self.url_input)
        layout.addWidget(self.question_label)
        layout.addWidget(self.question_input)
        layout.addWidget(self.ask_btn)
        layout.addWidget(self.gpt_response_output)

        self.setLayout(layout)

        # Set fixed size
        self.setFixedSize(QSize(500, 400))

    # Override the eventFilter method to handle the Enter key event
    def eventFilter(self, obj, event):
        if obj is self.question_input and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Enter:
            self.ask_gpt()
            return True
        return super().eventFilter(obj, event)

    def ask_gpt(self):
        url = self.url_input.text()
        user_question = self.question_input.toPlainText()  # Use toPlainText for QTextEdit

        if not url:
            self.gpt_response_output.clear()
            self.gpt_response_output.append("----- Please enter the URL first -----")
            return
        elif not user_question:
            self.gpt_response_output.clear()
            self.gpt_response_output.append("----- Please prompt something -----")
            return

        try:
            # Attempt to access the URL using requests
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad requests

            # Get and display the text content
            text_content = get_text_from_url(url)
            if text_content:
                # Save the extracted content in the list
                content_list.append(text_content)

                # Clear the output box
                self.gpt_response_output.clear()

                # Ask GPT-3.5 based on the extracted content
                try:
                    gpt_response = ask_gpt(user_question, content_list[0])

                    # Display the GPT response smoothly
                    self.print_smoothly(gpt_response)
                except Exception as e:
                    self.gpt_response_output.append(f"Error asking GPT-3.5: {e}")

        except requests.exceptions.RequestException as e:
            self.gpt_response_output.clear()
            self.gpt_response_output.append(f"Error accessing the website: {e}")

    def print_smoothly(self, response):
        for letter in response:
            self.gpt_response_output.insertPlainText(letter)
            self.gpt_response_output.moveCursor(QTextCursor.End)  # Move cursor to the end
            QApplication.processEvents()
            time.sleep(0.02)

def get_text_from_url(url):
    try:
        # Send a GET request to the URL with the user agent
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad requests

        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract only the main text content (excluding buttons, menus, etc.)
        text_content = ''
        for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text_content += tag.get_text() + '\n'

        return text_content

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def ask_gpt(question, context):
    max_context_length = 13000  # Maximum context length for GPT-3.5
    truncated_context = context[:max_context_length]

    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=f"Instructions: {truncated_context}\nQuestion: {question}\n",
        max_tokens=500,
    )
    return response.choices[0].text.strip()

def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))  # Set Fusion style for a modern look
    gpt_app = GPTApp()
    gpt_app.setWindowTitle("WikiGPT")
    gpt_app.show()

    try:
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

if __name__ == '__main__':
    main()
