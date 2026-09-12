# pie_chart.py
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from pathlib import Path
from typing import Union, Dict
from mplfonts import use_font
from adjustText import adjust_text
import numpy as np

class PieChart:
    """
    針對害蟲數量資料，產生餅圖並可輸出成圖片或 Base64。

    參數:
    - data (dict): 例如 {"薊馬": 3, "蚊子": 5, "粉蝨": 2, "未知": 1}
    - title (str): 圖表標題
    """
    def __init__(self, data: Dict[str, int], title: str = "害蟲比例"):
        self.data = data
        self.title = title
        use_font("Noto Sans CJK SC")

    def _prepare_data(self):
        """
        直接使用整個 dict 的 key-value 當作標籤與數值。
        若 sum(counts) == 0，代表沒有偵測到任何害蟲，則顯示「無害蟲偵測」。
        """
        filtered_data = {k: v for k, v in self.data.items() if k != "總數"}

        labels = list(filtered_data.keys())
        counts = list(filtered_data.values())

        # 如果 sum(counts) == 0，代表沒有偵測到任何害蟲
        if sum(counts) == 0:
            labels = ["無害蟲偵測"]
            counts = [1]

        return labels, counts
    
    def _calculate_density(self) -> float:
        """
        計算害蟲密度 (隻/cm²)。

        回傳:
        - density (float): 害蟲密度，單位為 隻/cm²
        """
        # paper_area_cm2 = 310.8  # A5 大小 (cm²)
        # total_count = self.data.get("總數", sum(self.data.values()))  # 若無 "總數"，則使用所有數量總和

        """
        計算害蟲密度 (隻/m²)。

        回傳:
        - density (float): 害蟲密度，單位為 隻/m²
        """

        paper_area_m2 = 0.03108  
        total_count = self.data.get("總數", sum(self.data.values()))  # 若無 "總數"，則使用所有數量總和

        return total_count / paper_area_m2  # 計算密度

    def save_image(self, output_path: Union[str, Path], format: str = 'jpg'):
        """
        將餅圖直接存成檔案。
        
        參數:
        - output_path (str | Path): 輸出檔案的路徑
        - format (str): 儲存格式 (預設為 'JPEG'，也可使用 'PNG' 等)
        """
        # this part is for pie chart ============================================
        # labels, counts = self._prepare_data()
        # density = int(round(self._calculate_density())) 
        # # title = f"害蟲密度：{density:.3f} 隻/cm²"  
        # title = f"害蟲密度：{density} 隻/m²"
        # plt.figure(figsize=(10, 10))
        # plt.pie(
        #     counts, labels=labels, autopct='%1.1f%%', startangle=90,
        #     textprops={'fontsize': 28}, radius=2.0, # 設定標籤和比例數字的字體大小
        #     pctdistance=0.9,
        #     labeldistance=1.1
        # )

        # plt.title(title, fontsize=35, pad=50)  # 設定標題字體大小
        # plt.axis('equal')  # 讓餅圖呈現正圓
        #=================================================================

        labels, counts = self._prepare_data()
        density = int(round(self._calculate_density()))  # 總密度（整數）

        fig, ax = plt.subplots(figsize=(10, 10))
        wedges, texts, autotexts = ax.pie(
            counts,
            autopct='%1.1f%%',          # 只顯示百分比數字
            startangle=90,
            wedgeprops=dict(width=0.4),  # width<1 → 中心留白
            pctdistance=0.85,           # 百分比顯示位置
            textprops={'fontsize': 20}
        )
        
        # 美化百分比文字（白色粗體）
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(22)

        # 1. 換成 Donut
        # fig, ax = plt.subplots(figsize=(10, 10))
        # wedges, _ = ax.pie(
        #     counts,
        #     startangle=90,
        #     wedgeprops=dict(width=0.4),  # width<1 → 中心留白
        #     labels=None                # 本體不顯示任何文字
        # )

        ax.set_aspect('equal')

        # 2. 標題（保留在上方）
        plt.title(f"總密度：{density:,} 隻/m²", fontsize=35, pad=50)
        # 3. 各類密度放到中央空白
        # area = 0.03108  # m²
        # lines = [
        #     f"{lab}：{int(round(cnt/area)):,} 隻/m²"
        #     for lab, cnt in zip(labels, counts)
        # ]
        # ax.text(0, 0,
        #     "\n".join(lines),
        #     ha="center", va="center",
        #     fontsize=24
        # )
        area = 0.03108  # m²
        # y 座標從頂到底平均切分，依 labels 長度決定
        y_positions = np.linspace(0.3, -0.3, len(labels))
        for y, lab, cnt, wedge in zip(y_positions, labels, counts, wedges):
            dens = int(round(cnt / area))
            ax.text(
                0, y,
                f"{lab}：{dens:,} 隻/m²",
                ha="center", va="center",
                fontsize=24,
                color=wedge.get_facecolor()  # 取對應的顏色
            )
        
        note = "註：害蟲密度是由黏蟲紙偵測所得害蟲隻數除以黏蟲紙面積換算求得"
        fig.text(0.5, 0.02, note,
                 ha="center", va="bottom",
                 fontsize=22, color="gray")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)  # 確保目錄存在
        # plt.savefig(output_path, format=format)
        plt.savefig(output_path, format=format, bbox_inches='tight', dpi=150)
        plt.close()

    def get_base64(self) -> str:
        """
        生成餅圖後，轉換成 Base64 字串並回傳。
        
        回傳:
        - str: Base64 編碼後的圖片字串，可直接在 JSON 或 HTML <img> 標籤中使用
        """
        labels, counts = self._prepare_data()

        plt.figure(figsize=(6, 6))
        plt.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title(self.title)
        plt.axis('equal')  # 讓餅圖呈現正圓

        buf = BytesIO()
        plt.savefig(buf, format='PNG')
        buf.seek(0)
        encoded_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
        plt.close()

        return encoded_str

def main():
    # 假設你偵測到的害蟲數量如下
    data = {
        "薊馬": 3,
        "蚊子": 5,
        "粉蝨": 2,
        "未知": 1
    }

    # 建立 PieChart 物件
    # chart = PieChart(data, title="害蟲比例測試")
    chart = PieChart(data, title="ggg")
    # 儲存成檔案，指定輸出路徑與格式
    output_path = "./my_pie.jpg"
    chart.save_image(output_path, format="jpg")

    print(f"Pie chart image saved successfully at: {output_path}")

if __name__ == "__main__":
    main()