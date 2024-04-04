import multiprocessing
import sys

from window import *


if __name__ == '__main__':
   
    if sys.gettrace():
        cryptoInit(logger())
    else:
        # If not set, pyinstaller executable will keep opening new windows
        multiprocessing.freeze_support()

        # quit app in command line with ctrl-c
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        app = QApplication(sys.argv)

        window = MainWindow()
        window.show()

        # Start the event loop.
        sys.exit(app.exec())