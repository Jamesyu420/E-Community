from ee import Ui_MainWindow
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout,QMainWindow,QApplication
from PyQt5.QtCore import Qt, QPoint,QCoreApplication
from PyQt5.QtGui import QFont, QCursor,QGuiApplication
import sys

import sys, os
if hasattr(sys, 'frozen'):    
    os.environ['PATH'] = sys._MEIPASS + ";" + os.environ['PATH']

class re_mainwindow(QMainWindow):
    
    def __init__(self,*args):
        super(re_mainwindow, self).__init__(*args)
        self._padding = 5
        self.initDrag()

    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton) and (event.pos() in self._corner_rect):
            self._corner_drag = True
            event.accept()
        elif (event.button() == Qt.LeftButton) and (event.pos() in self._right_rect):
            self._right_drag = True
            event.accept()
        elif (event.button() == Qt.LeftButton) and (event.pos() in self._bottom_rect):
            self._bottom_drag = True
            event.accept()
        elif (event.button() == Qt.LeftButton) and (event.y() < ui.headwidget.height()):
            self._move_drag = True
            self.move_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.pos() in self._corner_rect:
            self.setCursor(Qt.SizeFDiagCursor)
        elif QMouseEvent.pos() in self._bottom_rect:
            self.setCursor(Qt.SizeVerCursor)
        elif QMouseEvent.pos() in self._right_rect:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        if Qt.LeftButton and self._right_drag:
            self.resize(QMouseEvent.pos().x(), self.height())
            QMouseEvent.accept()
        elif Qt.LeftButton and self._bottom_drag:
            self.resize(self.width(), QMouseEvent.pos().y())
            QMouseEvent.accept()
        elif Qt.LeftButton and self._corner_drag:
            self.resize(QMouseEvent.pos().x(), QMouseEvent.pos().y())
            QMouseEvent.accept()
        elif Qt.LeftButton and self._move_drag:
            self.move(QMouseEvent.globalPos() - self.move_DragPosition)
            QMouseEvent.accept()

    def initDrag(self):
        self._move_drag = False
        self._corner_drag = False
        self._bottom_drag = False
        self._right_drag = False

    def mouseReleaseEvent(self, QMouseEvent):
        self._move_drag = False
        self._corner_drag = False
        self._bottom_drag = False
        self._right_drag = False

    def resizeEvent(self, QResizeEvent):        
        self._right_rect = [QPoint(x, y) for x in range(self.width() - self._padding, self.width() + 1)
                           for y in range(1, self.height() - self._padding)]
        self._bottom_rect = [QPoint(x, y) for x in range(1, self.width() - self._padding)
                         for y in range(self.height() - self._padding, self.height() + 1)]
        self._corner_rect = [QPoint(x, y) for x in range(self.width() - self._padding, self.width() + 1)
                                    for y in range(self.height() - self._padding, self.height() + 1)]


if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv) 
    MainWindow=re_mainwindow()
    ui = Ui_MainWindow()          
    ui.setupUi(MainWindow) 
    MainWindow.show()      
    sys.exit(app.exec_())  