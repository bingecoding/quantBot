import os
import signal

from PyQt6.QtCore import * #QSize, Qt, QRunnable, QThreadPool,
from PyQt6.QtWidgets import * #QApplication, QMainWindow, QPushButton
from PyQt6.QtMultimedia import (QAudioOutput, QMediaFormat, QMediaPlayer)
from PyQt6.QtGui import *

from cryptoWatcher import *

if __debug__:
    class logger:
        def emit(self, str):
            print(str)

class WorkerSignals(QObject):

    finished = pyqtSignal()
    triggerSaveImage = pyqtSignal(object)
    logger = pyqtSignal(object)
    mutex = QMutex()

class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

        self.signals = WorkerSignals()

        self.kwargs['logger'] = self.signals.logger

    @pyqtSlot()
    def run(self):
        # Retrieve args/kwargs here; and fire processing using them
        self.fn(**self.kwargs)

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Quant")
        self.resize(QSize(700, 400))

        #self.setLayout(QVBoxLayout())

        tool_bar = QToolBar()
        #self.addToolBar(tool_bar)
        tool_bar.setIconSize(QSize(24, 24))

        icon = QIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._play_action = tool_bar.addAction(icon, "Play")
        #self._play_action.triggered.connect(self.play)

        icon = QIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self._stop_action = tool_bar.addAction(icon, "Stop")
        #self._stop_action.triggered.connect(self.stop)

        widget = QWidget()
        layout = QVBoxLayout()

        widget.setLayout(layout)

        #self.logOutput = QTextEdit()
        self.logOutput = QTextBrowser()
        def handle_links(url):
            if not url.scheme():
                url = QUrl.fromLocalFile(url.toString())
            QDesktopServices.openUrl(url)

        self.logOutput.anchorClicked.connect(handle_links)
        self.logOutput.setOpenLinks(False) #will open file in text box if not set to False
        #self.logOutput.setOpenExternalLinks(False)
        #self.logOutput.setReadOnly(True)
        self.cursor = QTextCursor(self.logOutput.document())
        self.logOutput.setTextCursor(self.cursor)
        #self.logOutput.setDisabled(True)
        #self.logOutput.moveCursor(QTextCursor.MoveOperation.End)

        layout.addWidget(self.logOutput)
        self.setCentralWidget(widget)

        self.__startThread__()

    def __startThread__(self):
       
        self.threadpool = QThreadPool()

        self.worker = Worker(cryptoInit) # Any other args, kwargs are passed to the run function
        #self.worker.signals.triggerSaveImage.connect(self.saveImage)
        self.worker.signals.logger.connect(self.logText)

        # Execute
        self.threadpool.start(self.worker)       

    def logText(self, text):
        #self.logOutput.insertPlainText(text)
        self.logOutput.append(text)
        self.logOutput.moveCursor(QTextCursor.MoveOperation.End)

       # triggered when window is closed
    def closeEvent(self, event):
        event.accept()
        #self.worker.signals.finished.emit()
        os.kill(os.getpid(),signal.SIGINT)