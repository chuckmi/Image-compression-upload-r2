import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                           QComboBox, QSlider, QRadioButton, QLineEdit, QCheckBox,
                           QDialog, QFrame)
from PyQt6.QtCore import Qt, QMimeData, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QClipboard, QPainter, QColor, QIcon
from PIL import Image
import boto3
from datetime import datetime, timedelta
import shutil
import time
import threading
import json

# 直接在这里定义 R2_CONFIG
R2_CONFIG = {
    'endpoint_url': 'https://cb909aba4bc12157417c84091602de13.r2.cloudflarestorage.com',
    'aws_access_key_id': '20b04261ae2525599fa2123f0e899f37',
    'aws_secret_access_key': '7b75b9bd1209a6b77b8dcad0dc8ac22d51e1eddae19682e2ec64de998bf495c0',
    'bucket_name': 'pandatrips',
    'custom_domain': 'cdn.pandatrips.com'  # 可选
}

class UploadSuccessDialog(QDialog):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("上传成功")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # 添加说明标签
        label = QLabel("图片已上传成功！链接如下：")
        layout.addWidget(label)
        
        # 添加链接输入框
        self.url_input = QLineEdit(url)
        self.url_input.setReadOnly(True)
        layout.addWidget(self.url_input)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        
        copy_button = QPushButton("复制链接")
        copy_button.clicked.connect(self.copy_url)
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(copy_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def copy_url(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.url_input.text())
        self.parent().statusBar().showMessage("链接已复制到剪贴板！", 3000)

class ImageCompareWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setCursor(Qt.CursorShape.SplitHCursor)
        
        # 初始化变量
        self.original_pixmap = None
        self.compressed_pixmap = None
        self.split_position = 0.5  # 分割线位置（0-1之间）
        self.dragging = False
        
        # 设置鼠标追踪
        self.setMouseTracking(True)
        
    def set_images(self, original_path, compressed_path):
        # 加载并缩放图片
        original = QPixmap(original_path)
        compressed = QPixmap(compressed_path)
        
        # 保持宽高比例缩放到组件大小
        scaled_size = self.size()
        self.original_pixmap = original.scaled(scaled_size, 
                                             Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
        self.compressed_pixmap = compressed.scaled(scaled_size,
                                                 Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation)
        self.update()
        
    def paintEvent(self, event):
        if not self.original_pixmap or not self.compressed_pixmap:
            return
            
        painter = QPainter(self)
        
        # 计算图片在组件中的居中位置
        x = (self.width() - self.original_pixmap.width()) // 2
        y = (self.height() - self.original_pixmap.height()) // 2
        
        # 绘制原图
        painter.drawPixmap(x, y, self.original_pixmap)
        
        # 计算分割线位置
        split_x = x + int(self.original_pixmap.width() * self.split_position)
        
        # 绘制压缩后的图片（右半部分）
        painter.setClipRect(split_x, y, 
                          self.width() - split_x, 
                          self.compressed_pixmap.height())
        painter.drawPixmap(x, y, self.compressed_pixmap)
        
        # 绘制分割线
        painter.setClipping(False)
        pen = painter.pen()
        pen.setColor(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(split_x, y, 
                        split_x, y + self.original_pixmap.height())
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            
    def mouseMoveEvent(self, event):
        if not self.original_pixmap:
            return
            
        # 计算图片在组件中的x坐标
        x = (self.width() - self.original_pixmap.width()) // 2
        
        if self.dragging:
            # 计算分割线位置（相对于图片）
            rel_x = event.position().x() - x
            self.split_position = max(0, min(1, rel_x / self.original_pixmap.width()))
            self.update()

class R2ConfigDialog(QDialog):
    def __init__(self, r2_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置 R2")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # 创建输入框
        self.endpoint_input = QLineEdit(r2_config['endpoint_url'])
        self.access_key_input = QLineEdit(r2_config['aws_access_key_id'])
        self.secret_key_input = QLineEdit(r2_config['aws_secret_access_key'])
        self.bucket_name_input = QLineEdit(r2_config['bucket_name'])
        self.custom_domain_input = QLineEdit(r2_config['custom_domain'])
        
        # 添加输入框到布局
        layout.addWidget(QLabel("R2 终端节点:"))
        layout.addWidget(self.endpoint_input)
        layout.addWidget(QLabel("访问密钥 ID:"))
        layout.addWidget(self.access_key_input)
        layout.addWidget(QLabel("访问密钥:"))
        layout.addWidget(self.secret_key_input)
        layout.addWidget(QLabel("存储桶名称:"))
        layout.addWidget(self.bucket_name_input)
        layout.addWidget(QLabel("自定义域名:"))
        layout.addWidget(self.custom_domain_input)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_config(self):
        """获取配置"""
        return {
            'endpoint_url': self.endpoint_input.text(),
            'aws_access_key_id': self.access_key_input.text(),
            'aws_secret_access_key': self.secret_key_input.text(),
            'bucket_name': self.bucket_name_input.text(),
            'custom_domain': self.custom_domain_input.text()
        }

class ImageProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置窗口标题
        self.setWindowTitle("Panda图片压缩工具")
        
        # 设置窗口图标
        app_icon = QIcon("icon.png")  # 确保 icon.png 在程序目录下
        self.setWindowIcon(app_icon)
        
        self.setMinimumSize(1200, 800)
        
        # 初始化变量
        self.original_image_path = None
        self.compressed_image_path = None
        
        # 创建缓存目录
        self.cache_dir = os.path.join(os.path.expanduser('~'), '.pandatrips_cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 配置文件路径
        self.config_path = os.path.join(self.cache_dir, 'settings.json')
        
        # 加载上次的配置
        self.load_settings()
        
        # 加载 R2 配置
        self.load_r2_config()
            
        # 启动缓存清理线程
        self.start_cache_cleaner()
        
        self.init_ui()
        
    def load_settings(self):
        """加载上次的配置"""
        self.settings = {
            'format': 'webp',
            'quality': 80,
            'save_original': True,  # 默认勾选保存原图
            'upload_r2': True,      # 默认勾选上传R2
            'auto_name': True
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
    
    def save_settings(self):
        """保存当前配置"""
        try:
            current_settings = {
                'format': self.format_combo.currentText(),
                'quality': self.quality_slider.value(),
                'save_original': self.save_original.isChecked(),
                'upload_r2': self.save_to_r2.isChecked(),
                'auto_name': self.auto_name_radio.isChecked()
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(current_settings, f)
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
    
    def load_r2_config(self):
        """加载 R2 配置"""
        self.r2_config = {
            'endpoint_url': '',
            'aws_access_key_id': '',
            'aws_secret_access_key': '',
            'bucket_name': '',
            'custom_domain': ''
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    self.r2_config.update(saved_settings.get('r2_config', {}))
        except Exception as e:
            print(f"加载 R2 配置失败: {str(e)}")
    
    def init_ui(self):
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建分隔线函数
        def add_separator():
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            return line
        
        # 创建主布局
        layout = QHBoxLayout()
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)  # 减小组件之间的间距
        left_layout.setContentsMargins(10, 10, 10, 10)  # 减小边距
        
        # 添加软件 Logo
        logo_label = QLabel()
        # 使用 QPixmap 加载图片，如果加载失败则使用文字替代
        logo_pixmap = QPixmap("panda.png")
        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio)
            logo_label.setPixmap(scaled_logo)
        else:
            # 如果图片加载失败，使用文字图标
            logo_label.setText("🖼️")
            logo_label.setStyleSheet("""
                QLabel {
                    font-size: 24px;
                    padding: 8px;
                }
            """)
        
        # 创建标题容器
        title_container = QHBoxLayout()
        title_container.setSpacing(10)  # logo 和文字之间的间距
        
      
        
        # 添加弹性空间,使 Logo 和标题文字靠左对齐
        title_container.addStretch()
        
        # 添加标题容器到左侧布局
        left_layout.addLayout(title_container)
        left_layout.addWidget(add_separator())  # 在标题下方添加分隔线
        
        # 图片选择区域
        self.select_label = QLabel("选择图片")
        self.select_button = QPushButton("选择图片或者拖拽到此处")
        self.select_button.setMinimumHeight(60)  # 减小按钮高度
        self.select_button.clicked.connect(self.select_image)
        
        # 格式选择区域 - 使用水平布局
        format_container = QHBoxLayout()
        format_label = QLabel("格式:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["webp", "jpeg", "png"])
        format_container.addWidget(format_label)
        format_container.addWidget(self.format_combo)
        
        # 质量滑块区域
        quality_container = QHBoxLayout()
        quality_label = QLabel("质量:")
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(80)
        self.quality_value = QLabel("80%")
        self.quality_value.setMinimumWidth(40)
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_value.setText(f"{v}%"))
        quality_container.addWidget(quality_label)
        quality_container.addWidget(self.quality_slider)
        quality_container.addWidget(self.quality_value)
        
        # 压缩按钮 - 设置更大的尺寸和样式
        self.compress_button = QPushButton("压缩图片")
        self.compress_button.setMinimumHeight(40)  # 增加按钮高度
        self.compress_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.compress_button.clicked.connect(self.compress_image)
        
        # 文件命名选项 - 使用水平布局
        name_container = QHBoxLayout()
        self.auto_name_radio = QRadioButton("自动")
        self.custom_name_radio = QRadioButton("自定义")
        name_container.addWidget(self.auto_name_radio)
        name_container.addWidget(self.custom_name_radio)
        
        # 自定义名称输入框
        self.name_input = QLineEdit()
        self.name_input.setEnabled(False)
        self.name_input.setPlaceholderText("输入自定义文件名")
        
        # 保存选项 - 使用水平布局
        save_options = QHBoxLayout()
        self.save_original = QCheckBox("保存原图")
        self.save_to_r2 = QCheckBox("上传R2")
        save_options.addWidget(self.save_original)
        save_options.addWidget(self.save_to_r2)
        
        # 保存按钮 - 设置更大的尺寸和样式
        self.save_button = QPushButton("保存")
        self.save_button.setMinimumHeight(40)  # 增加按钮高度
        self.save_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.save_button.clicked.connect(self.save_image)
        
        # 在左侧面板底部添加链接显示区域
        link_container = QVBoxLayout()
        link_label = QLabel("最近上传链接:")
        self.link_text = QLineEdit()
        self.link_text.setReadOnly(True)
        self.link_text.setPlaceholderText("暂无上传链接")
        
        # 复制链接按钮 - 设置更大的尺寸和样式
        copy_link_btn = QPushButton("复制链接")
        copy_link_btn.setMinimumHeight(40)  # 增加按钮高度
        copy_link_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                background-color: #FF9800;
                color: white;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        copy_link_btn.clicked.connect(self.copy_last_link)
        
        link_container.addWidget(link_label)
        link_container.addWidget(self.link_text)
        link_container.addWidget(copy_link_btn)
        
        # 添加组件到左侧面板
        left_layout.addWidget(self.select_label)
        left_layout.addWidget(self.select_button)
        left_layout.addWidget(add_separator())
        left_layout.addLayout(format_container)
        left_layout.addLayout(quality_container)
        left_layout.addWidget(self.compress_button)
        left_layout.addWidget(add_separator())
        left_layout.addWidget(QLabel("文件命名:"))
        left_layout.addLayout(name_container)
        left_layout.addWidget(self.name_input)
        left_layout.addWidget(add_separator())
        left_layout.addLayout(save_options)
        left_layout.addWidget(self.save_button)
        left_layout.addWidget(add_separator())  # 在链接区域上方添加分隔线
        left_layout.addLayout(link_container)  # 添加链接显示区域
        left_layout.addStretch()  # 添加弹性空间
        
        # 添加 R2 配置按钮
        r2_config_button = QPushButton("配置 R2")
        r2_config_button.clicked.connect(self.open_r2_config_dialog)
        left_layout.addWidget(r2_config_button)
        
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(300)  # 限制左侧面板最大宽度
        
        # 右侧预览面板
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # 添加图片大小信息标签
        size_info = QHBoxLayout()
        self.original_size_label = QLabel("原图大小: 0KB")
        self.compressed_size_label = QLabel("压缩后大小: 0KB")
        size_info.addWidget(self.original_size_label)
        size_info.addWidget(self.compressed_size_label)
        right_layout.addLayout(size_info)
        
        # 添加图片对比组件
        self.image_compare = ImageCompareWidget()
        right_layout.addWidget(self.image_compare)
        
        right_panel.setLayout(right_layout)
        
        # 设置主布局
        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel, 2)
        main_widget.setLayout(layout)
        
        # 设置拖放
        self.setAcceptDrops(True)
        
        # 初始化按钮状态
        self.compress_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
        # 连接单选按钮信号
        self.auto_name_radio.toggled.connect(
            lambda: self.name_input.setEnabled(False))
        self.custom_name_radio.toggled.connect(
            lambda: self.name_input.setEnabled(True))
        self.auto_name_radio.setChecked(True)
        
        # 设置格式选择
        format_index = self.format_combo.findText(self.settings['format'])
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)
        
        # 设置质量滑块
        self.quality_slider.setValue(self.settings['quality'])
        
        # 设置命名方式
        if self.settings['auto_name']:
            self.auto_name_radio.setChecked(True)
        else:
            self.custom_name_radio.setChecked(True)
        
        # 设置保存选项
        self.save_original.setChecked(self.settings['save_original'])
        self.save_to_r2.setChecked(self.settings['upload_r2'])
        
        # 连接信号以保存设置
        self.format_combo.currentTextChanged.connect(self.save_settings)
        self.quality_slider.valueChanged.connect(self.save_settings)
        self.save_original.toggled.connect(self.save_settings)
        self.save_to_r2.toggled.connect(self.save_settings)
        self.auto_name_radio.toggled.connect(self.save_settings)
        
        # 检查 R2 配置是否存在
        if not self.r2_config['endpoint_url']:
            self.open_r2_config_dialog()  # 如果没有配置，打开配置对话框

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = event.mimeData().urls()
        if files:
            image_path = files[0].toLocalFile()
            self.load_image(image_path)

    def select_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_name:
            self.load_image(file_name)

    def load_image(self, image_path):
        self.original_image_path = image_path
        # 显示原图预览
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_compare.set_images(image_path, image_path)
        
        # 显示原图大小
        size = os.path.getsize(image_path)
        self.original_size_label.setText(f"原图大小: {size/1024:.1f}KB")
        
        # 启用压缩按钮
        self.compress_button.setEnabled(True)

    def start_cache_cleaner(self):
        """启动缓存清理线程"""
        def clean_cache():
            while True:
                try:
                    # 获取当前时间
                    now = datetime.now()
                    # 遍历缓存目录
                    for filename in os.listdir(self.cache_dir):
                        file_path = os.path.join(self.cache_dir, filename)
                        # 获取文件修改时间
                        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        # 如果文件超过100天，删除它
                        if now - mtime > timedelta(days=100):
                            try:
                                os.remove(file_path)
                            except:
                                pass
                except Exception as e:
                    print(f"Cache cleaning error: {str(e)}")
                # 每天检查一次
                time.sleep(24 * 60 * 60)
        
        # 创建并启动清理线程
        cleaner = threading.Thread(target=clean_cache, daemon=True)
        cleaner.start()

    def compress_image(self):
        if not self.original_image_path:
            return
            
        # 打开原图
        image = Image.open(self.original_image_path)
        
        # 获取保存格式和质量
        format = self.format_combo.currentText()
        quality = self.quality_slider.value()
        
        # 在缓存目录中创建临时文件
        temp_filename = f"compressed_{int(time.time())}.{format}"
        temp_path = os.path.join(self.cache_dir, temp_filename)
        image.save(temp_path, format=format, quality=quality)
        
        # 更新图片预览
        self.image_compare.set_images(self.original_image_path, temp_path)
        
        # 更新文件大小显示
        original_size = os.path.getsize(self.original_image_path)
        compressed_size = os.path.getsize(temp_path)
        self.original_size_label.setText(f"原图大小: {original_size/1024:.1f}KB")
        self.compressed_size_label.setText(f"压缩后大小: {compressed_size/1024:.1f}KB")
        
        self.compressed_image_path = temp_path
        self.save_button.setEnabled(True)

    def save_image(self):
        if not self.compressed_image_path:
            return
            
        try:
            # 获取文件名
            if self.auto_name_radio.isChecked():
                original_name = os.path.splitext(os.path.basename(self.original_image_path))[0]
                filename = f"{original_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                filename = self.name_input.text()
            
            format = self.format_combo.currentText()
            
            # 获取原始图片所在的目录
            original_dir = os.path.dirname(self.original_image_path)
            
            # 在当前目录保存压缩后的图片
            current_save_path = f"{filename}.{format}"
            shutil.copy2(self.compressed_image_path, current_save_path)
            
            # 如果选择了保存原图，则在原始图片目录也保存一份
            if self.save_original.isChecked():
                original_dir_save_path = os.path.join(original_dir, f"{filename}.{format}")
                shutil.copy2(self.compressed_image_path, original_dir_save_path)
                self.statusBar().showMessage(f"图片已保存: {current_save_path} 和 {original_dir_save_path}")
            else:
                self.statusBar().showMessage(f"图片已保存: {current_save_path}")
            
            # 上传到R2
            if self.save_to_r2.isChecked():
                self.upload_to_r2(current_save_path)
            
        except Exception as e:
            self.statusBar().showMessage(f"保存失败: {str(e)}")
        finally:
            # 清理临时文件
            try:
                if os.path.exists(self.compressed_image_path):
                    os.remove(self.compressed_image_path)
            except:
                pass

    def copy_last_link(self):
        """复制链接到剪贴板"""
        if self.link_text.text():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.link_text.text())
            self.statusBar().showMessage("链接已复制到剪贴板！", 3000)

    def upload_to_r2(self, file_path):
        try:
            # 配置R2客户端
            s3 = boto3.client('s3',
                endpoint_url=self.r2_config['endpoint_url'],
                aws_access_key_id=self.r2_config['aws_access_key_id'],
                aws_secret_access_key=self.r2_config['aws_secret_access_key'],
                region_name='auto'
            )
            
            # 获取当前日期作为目录路径
            today = datetime.now()
            date_path = today.strftime("%Y/%m%d")  # 格式如: 2024/03/14
            
            # 构建完整的文件路径
            file_name = os.path.basename(file_path)
            r2_path = f"{date_path}/{file_name}"  # 例如: 2024/03/14/image.jpg
            
            # 上传文件
            s3.upload_file(file_path, self.r2_config['bucket_name'], r2_path)
            
            # 获取文件URL
            if 'custom_domain' in self.r2_config:
                url = f"https://{self.r2_config['custom_domain']}/{r2_path}"
            else:
                url = f"https://{self.r2_config['bucket_name']}.r2.cloudflarestorage.com/{r2_path}"
            
            # 更新链接显示
            self.link_text.setText(url)
            self.statusBar().showMessage(f"文件已上传到R2: {url}")
            
        except Exception as e:
            self.statusBar().showMessage(f"上传到R2失败: {str(e)}")

    def open_r2_config_dialog(self):
        dialog = R2ConfigDialog(self.r2_config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.r2_config = dialog.get_config()
            self.save_r2_config()

    def save_r2_config(self):
        """保存 R2 配置"""
        try:
            current_settings = {
                'r2_config': self.r2_config
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(current_settings, f)
        except Exception as e:
            print(f"保存 R2 配置失败: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.png"))  # 设置应用程序图标
    window = ImageProcessor()
    window.show()
    sys.exit(app.exec()) 