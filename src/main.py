import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QListWidget, QFileDialog, QMessageBox, QSplitter, QLabel, QDialog, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal
from chat_manager import ChatDatabase
from mirbot_client import MirBotClient, system_prompt
import time
from PySide6.QtGui import QIcon
import os


def resource_path(relative_path):
  
    try:
        base_path = sys._MEIPASS 
    except Exception:
        base_path = os.path.abspath(".") 
    return os.path.join(base_path, relative_path)
class BotThread(QThread):
    finished = Signal(str)

    def __init__(self, client, message):
        super().__init__()
        self.client = client
        self.message = message

    def run(self):
        try:
            reply = self.client.get_best_response(self.message)
            self.finished.emit(reply)
        except Exception as e:
            self.finished.emit(f"❌ خطا در پردازش پیام: {e}")



class HistoryDialog(QDialog):
    def __init__(self, db: ChatDatabase):
        super().__init__()
        self.setWindowTitle("تاریخچه چت‌ها")
        self.resize(500, 400)
        self.setWindowIcon(QIcon('icon.ico'))

        self.db = db
        self.list_widget = QListWidget()
        self.load_history()

        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def load_history(self):
        self.list_widget.clear()
        for chat_id, title in self.db.get_chats():
            self.list_widget.addItem(QListWidgetItem(f"{chat_id}: {title}"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MirBot AI - Desktop")
        self.resize(1200, 700)
        self.setWindowIcon(QIcon('icon.ico'))

        self.db = ChatDatabase()
        self.client = MirBotClient(system_prompt=system_prompt)
        self.current_chat_id = self.db.new_chat()

        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.load_selected_chat)

      
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("font-size: 14px;")

        
        self.loading_label = QLabel("⏳ در حال پردازش...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.hide()

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("پیام خود را بنویسید...")
        self.send_btn = QPushButton("ارسال")
        self.send_btn.clicked.connect(self.send_message)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_btn)

        chat_layout = QVBoxLayout()
        chat_layout.addWidget(self.chat_display)
        chat_layout.addWidget(self.loading_label)
        chat_layout.addLayout(input_layout)

     
        splitter = QSplitter(Qt.Horizontal)
        sidebar = QWidget()
        s_layout = QVBoxLayout(sidebar)
        s_layout.addWidget(self.chat_list)

        chat_area = QWidget()
        chat_area.setLayout(chat_layout)

        splitter.addWidget(sidebar)
        splitter.addWidget(chat_area)
        splitter.setStretchFactor(1, 3)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

   
        menu = self.menuBar().addMenu("گزینه‌ها")
        new_chat = menu.addAction("چت جدید")
        new_chat.triggered.connect(self.new_chat)
        export_chat = menu.addAction("خروجی TXT")
        export_chat.triggered.connect(self.export_chat)
        history_action = menu.addAction("تاریخچه")
        history_action.triggered.connect(self.show_history)
        clear_history_action = menu.addAction("پاک کردن تاریخچه")
        clear_history_action.triggered.connect(self.clear_history)
        exit_action = menu.addAction("خروج")
        exit_action.triggered.connect(self.close)

        self.load_chats()

    def load_chats(self):
        self.chat_list.clear()
        for chat_id, title in self.db.get_chats():
            self.chat_list.addItem(f"{chat_id}: {title}")

    def load_selected_chat(self, item):
        chat_id = int(item.text().split(":")[0])
        self.current_chat_id = chat_id
        self.chat_display.clear()
        for sender, content in self.db.get_messages(chat_id):
            self.chat_display.append(f"{sender}: {content}")

    def new_chat(self):
        self.current_chat_id = self.db.new_chat()
        self.load_chats()
        self.chat_display.clear()

   
    def send_message(self):
        msg = self.message_input.text().strip()
        if not msg:
            return

        self.db.add_message(self.current_chat_id, "👤 شما", msg)
        self.chat_display.append(f"👤 شما: {msg}")
        self.message_input.clear()

      
        self.loading_label.show()
        self.send_btn.setEnabled(False)

     
        self.thread = BotThread(self.client, msg)
        self.thread.finished.connect(self.receive_reply)
        self.thread.start()

    def receive_reply(self, reply):
        self.loading_label.hide()
        self.send_btn.setEnabled(True)

        self.db.add_message(self.current_chat_id, "🤖 ربات", reply)
        self.chat_display.append(f"🤖 ربات: {reply}")

  
    def export_chat(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره چت", "", "Text Files (*.txt)")
        if path:
            messages = self.db.get_messages(self.current_chat_id)
            with open(path, "w", encoding="utf-8") as f:
                for sender, content in messages:
                    f.write(f"{sender}: {content}\n")
            QMessageBox.information(self, "ذخیره شد", "چت ذخیره شد!")

   
    def show_history(self):
        dlg = HistoryDialog(self.db)
        dlg.exec()

 
    def clear_history(self):
        reply = QMessageBox.question(
            self,
            "تایید پاک کردن",
            "همه تاریخچه چت‌ها پاک شود؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.clear_all() 
            self.load_chats()
            self.chat_display.clear()
            QMessageBox.information(self, "پاک شد", "تمام تاریخچه چت‌ها پاک شد.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        with open(resource_path("ui.qss"), "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

