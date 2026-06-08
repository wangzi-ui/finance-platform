"""
报告生成模块
"""
import pandas as pd
from datetime import datetime
import os


class ReportGenerator:
    def __init__(self, output_dir='./reports'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_excel(self, data_dict, filename=None):
        if filename is None:
            filename = f"report_{datetime.now().strftime('%Y%m%d')}.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            has_sheet = False
            for sheet_name, df in data_dict.items():
                if df is not None:
                    if isinstance(df, dict):
                        df = pd.DataFrame([df])
                    elif not isinstance(df, pd.DataFrame):
                        df = pd.DataFrame(df)
                    if hasattr(df, 'empty') and not df.empty:
                        df.to_excel(writer, sheet_name=str(sheet_name)[:31], index=False)
                        has_sheet = True
            if not has_sheet:
                pd.DataFrame({'提示': ['暂无数据']}).to_excel(writer, sheet_name='空报告', index=False)
        return filepath

    def generate_summary_text(self, market_analysis, recommendations):
        summary = f"""
========================================
  智能投资分析报告
  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
========================================

【市场状态】: {market_analysis.get('market_status', '未知')}
【操作策略】: {market_analysis.get('strategy', '请谨慎操作')}
【上涨板块占比】: {market_analysis.get('up_ratio', 0)}%

----------------------------------------
  推荐基金 TOP 5:
----------------------------------------
"""
        if recommendations is not None and len(recommendations) > 0:
            for i, (_, row) in enumerate(recommendations.head(5).iterrows()):
                summary += f"""
{i+1}. {row.get('name', '未知')} ({row.get('code', '')})
   近1月收益: {row.get('month_return', 0):.2f}%
   近3月收益: {row.get('q3_return', 0):.2f}%
   近1年收益: {row.get('year_return', 0):.2f}%
   技术信号: {row.get('tech_recommendation', '未知')}
   预测方向: {row.get('predicted_direction', '未知')}
"""
        summary += """
----------------------------------------
  免责声明:
  本报告由AI生成，仅供参考，不构成投资建议。
  投资有风险，入市需谨慎。
========================================
"""
        return summary