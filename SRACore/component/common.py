from PySide6.QtWidgets import QWidget


class SRAComponent(QWidget):
    """
    SRA组件基类，所有组件都应继承自此类。
    """

    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = None

    def init(self):
        """
        初始化组件，依次调用预连接、设置器、连接器和获取器方法。
        :return: None
        """
        self.pre_connector()
        self.setter()
        self.connector()

    def pre_connector(self):
        """
        需要提前连接的信号和槽。
        :return: None
        """
        pass

    def setter(self):
        """
        从配置文件中读取数据并设置到UI组件上。
        :return: None
        """
        pass

    def connector(self):
        """
        连接UI组件的信号和槽。
        :return: None
        """
        pass

    def getter(self):
        """
        从UI组件中获取数据并保存到配置文件中。
        :return: None
        """
        pass
