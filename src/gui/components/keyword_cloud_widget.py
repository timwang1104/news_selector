import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from wordcloud import WordCloud

class KeywordCloudWidget(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.fig, self.ax = plt.subplots(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor('white')
        self.ax.axis('off')

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def update_wordcloud(self, keywords_data=None):
        """根据提供的关键词数据更新词云图"""
        if not keywords_data:
            keywords_data = {'暂无数据': 1}

        # 查找系统中的中文字体
        font_path = self._find_font()
        if not font_path:
            print("警告: 未找到中文字体, 词云中的中文可能无法正确显示。")
            # 可以在此处添加备用逻辑，例如使用默认字体

        wordcloud = WordCloud(
            width=800,
            height=600,
            background_color='white',
            font_path=font_path,  # 设置字体路径
            colormap='viridis',
            max_words=100
        ).generate_from_frequencies(keywords_data)

        self.ax.clear()
        self.ax.imshow(wordcloud, interpolation='bilinear')
        self.ax.axis('off')
        self.canvas.draw()

    def _find_font(self):
        """在系统中查找可用的中文字体"""
        import matplotlib.font_manager as fm
        # 常见中文字体列表
        font_list = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Heiti SC', 'sans-serif']
        for font_name in font_list:
            try:
                font_path = fm.findfont(fm.FontProperties(family=font_name))
                if font_path:
                    return font_path
            except Exception:
                continue
        return None

if __name__ == '__main__':
    root = tk.Tk()
    root.title("关键词云图测试")
    root.geometry("800x600")

    cloud_widget = KeywordCloudWidget(root)
    cloud_widget.pack(fill="both", expand=True)

    # 模拟数据
    test_data = {
        'AI': 85, '人工智能': 80, '机器学习': 75, '深度学习': 70,
        '区块链': 60, '云计算': 55, '物联网': 50, '5G': 45,
        '自动驾驶': 40, '大数据': 35, '创业': 30, '科技': 25
    }
    cloud_widget.update_wordcloud(test_data)

    root.mainloop()