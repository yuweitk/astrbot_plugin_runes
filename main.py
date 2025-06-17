from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import random
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import astrbot.api.message_components as Comp

# 加载符文数据
def load_runes_data() -> List[Dict]:
    runes_file = Path(__file__).parent / "runes.json"
    with open(runes_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("runes", [])

RUNES = load_runes_data()

@register("runes_divination", "雨爲/yuweitk", "基于LLM的卢恩符文占卜插件", "1.0.0", 
          "https://github.com/yuweitk/astrbot_plugin_runes")
class RunesDivinationPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = context._config if hasattr(context, '_config') else {}
        logger.info("卢恩占卜插件已加载")
        
    async def terminate(self):
        logger.info("卢恩占卜插件已卸载")

    @filter.command("卢恩占卜")
    async def runes_divination(self, event: AstrMessageEvent, method: str = None, question: str = None):
        """卢恩符文占卜系统
        使用方法: 卢恩占卜 [占卜方式] [问题(可选)]
        
        占卜方式:
        - 单符: 抽取一个符文进行简单占卜
        - 三符: 过去、现在、未来三符文占卜
        - 五符: 五符文十字占卜法
        - 九符: 九符文世界之树占卜法
        - 符文表: 显示所有符文及其含义
        
        示例:
        - 卢恩占卜 单符 我今天运势如何
        - 卢恩占卜 三符 我的感情发展
        - 卢恩占卜 符文表
        """
        if not method:
            yield event.plain_result("请指定占卜方式: 单符/三符/五符/九符/符文表\n示例: 卢恩占卜 单符 我今天运势如何")
            return
            
        method = method.lower()
        
        if method == "符文表":
            async for result in self.show_runes_table(event):
                yield result
            return
            
        if method not in ["单符", "三符", "五符", "九符"]:
            yield event.plain_result("无效的占卜方式，请使用: 单符/三符/五符/九符/符文表")
            return
            
        if not question:
            question = "我想知道关于未来的指引"
            
        # 根据配置获取解释深度
        interpretation_depth = self.config.get("interpretation_depth", "详细")
        include_history = self.config.get("include_history", True)
        
        # 根据不同的占卜方式处理
        if method == "单符":
            async for result in self.single_rune_divination(event, question, interpretation_depth, include_history):
                yield result
        elif method == "三符":
            async for result in self.three_runes_divination(event, question, interpretation_depth, include_history):
                yield result
        elif method == "五符":
            async for result in self.five_runes_divination(event, question, interpretation_depth, include_history):
                yield result
        elif method == "九符":
            async for result in self.nine_runes_divination(event, question, interpretation_depth, include_history):
                yield result
    
    async def show_runes_table(self, event: AstrMessageEvent):
        """显示所有符文及其含义"""
        runes_info = []
        for rune in RUNES:
            rune_info = (
                f"符文: {rune['symbol']} {rune['name']} ({rune['english_name']})\n"
                f"含义: {rune['meaning']}\n"
                f"逆位: {rune['reversed_meaning']}\n"
                f"关键词: {', '.join(rune['keywords'])}\n"
                f"类别: {rune['category']}\n"
            )
            runes_info.append(rune_info)
        
        # 使用LLM整理输出
        prompt = (
            "请将以下卢恩符文信息整理成清晰易读的格式:\n\n" + 
            "\n\n".join(runes_info) +
            "\n\n请按类别分组展示符文信息，每组之间用分隔线隔开。"
        )
        
        yield event.request_llm(
            prompt=prompt,
            system_prompt="你是一个专业的卢恩符文占卜师，请将符文信息整理成清晰易读的格式，按类别分组展示。"
        )
    
    async def single_rune_divination(self, event: AstrMessageEvent, question: str, 
                                   interpretation_depth: str, include_history: bool):
        """单符文占卜"""
        rune = self.draw_runes(1)[0]
        is_reversed = random.choice([True, False])
        
        # 先显示抽到的符文
        yield event.plain_result(
            f"您抽到的符文是: {rune['symbol']} {rune['name']} ({'逆位' if is_reversed else '正位'})\n"
            f"正在为您解读..."
        )
        
        # 构建提示词
        prompt = (
            f"问题: {question}\n\n"
            f"抽到的符文: {rune['symbol']} {rune['name']} ({'逆位' if is_reversed else '正位'})\n\n"
            f"请根据{'逆位' if is_reversed else '正位'}符文的含义，"
            f"为这个问题提供{'简要' if interpretation_depth == '简洁' else '详细' if interpretation_depth == '详细' else '深入'}的解读。"
        )
        
        if include_history:
            prompt += (
                f"\n\n请包含一些关于{rune['name']}符文的历史背景和北欧神话中的相关故事。"
            )
        
        yield event.request_llm(
            prompt=prompt,
            system_prompt=(
                "你是一个专业的卢恩符文占卜师，精通北欧神话和符文象征意义。"
                "请根据用户抽到的符文和问题，提供通俗易懂质朴且有文化内涵的占卜解读。"
            )
        )
    
    async def three_runes_divination(self, event: AstrMessageEvent, question: str, 
                                    interpretation_depth: str, include_history: bool):
        """三符文占卜 (过去-现在-未来)"""
        runes = self.draw_runes(3)
        reversed_status = [random.choice([True, False]) for _ in range(3)]
        
        # 先显示抽到的符文
        rune_display = "您抽到的符文是:\n"
        for i, rune in enumerate(runes):
            rune_display += (
                f"{['过去', '现在', '未来'][i]}: "
                f"{rune['symbol']} {rune['name']} ({'逆位' if reversed_status[i] else '正位'})\n"
            )
        yield event.plain_result(rune_display + "\n正在为您解读...")
        
        # 构建提示词
        prompt = (
            f"问题: {question}\n\n"
            f"三符文占卜结果:\n"
            f"1. 过去: {runes[0]['symbol']} {runes[0]['name']} ({'逆位' if reversed_status[0] else '正位'})\n"
            f"2. 现在: {runes[1]['symbol']} {runes[1]['name']} ({'逆位' if reversed_status[1] else '正位'})\n"
            f"3. 未来: {runes[2]['symbol']} {runes[2]['name']} ({'逆位' if reversed_status[2] else '正位'})\n\n"
            f"请根据这三个符文的正逆位关系，分析过去、现在和未来的发展脉络，"
            f"提供{'简要' if interpretation_depth == '简洁' else '详细' if interpretation_depth == '详细' else '深入'}的解读。"
        )
        
        if include_history:
            prompt += (
                "\n\n请包含一些关于这些符文的历史背景和北欧神话中的相关故事，"
                "特别是它们如何相互作用形成连贯的叙事。"
            )
        
        yield event.request_llm(
            prompt=prompt,
            system_prompt=(
                "你是一个专业的卢恩符文占卜师，精通北欧神话和符文象征意义。"
                "请根据用户抽到的三个符文和问题，分析过去、现在和未来的发展脉络，"
                "提供专业且有连贯性的占卜解读。"
            )
        )
    
    async def five_runes_divination(self, event: AstrMessageEvent, question: str, 
                                   interpretation_depth: str, include_history: bool):
        """五符文十字占卜法"""
        runes = self.draw_runes(5)
        reversed_status = [random.choice([True, False]) for _ in range(5)]
        
        # 先显示抽到的符文
        positions = ["中心(现状)", "上方(挑战)", "下方(建议)", "左方(助力)", "右方(结果)"]
        rune_display = "您抽到的符文是:\n"
        for i, rune in enumerate(runes):
            rune_display += (
                f"{positions[i]}: "
                f"{rune['symbol']} {rune['name']} ({'逆位' if reversed_status[i] else '正位'})\n"
            )
        yield event.plain_result(rune_display + "\n正在为您解读...")
        
        # 构建提示词
        prompt = (
            f"问题: {question}\n\n"
            f"五符文十字占卜结果:\n"
            f"1. 中心(现状): {runes[0]['symbol']} {runes[0]['name']} ({'逆位' if reversed_status[0] else '正位'})\n"
            f"2. 上方(挑战): {runes[1]['symbol']} {runes[1]['name']} ({'逆位' if reversed_status[1] else '正位'})\n"
            f"3. 下方(建议): {runes[2]['symbol']} {runes[2]['name']} ({'逆位' if reversed_status[2] else '正位'})\n"
            f"4. 左方(助力): {runes[3]['symbol']} {runes[3]['name']} ({'逆位' if reversed_status[3] else '正位'})\n"
            f"5. 右方(结果): {runes[4]['symbol']} {runes[4]['name']} ({'逆位' if reversed_status[4] else '正位'})\n\n"
            f"请根据这五个符文的正逆位关系，分析现状、挑战、建议、助力和可能的结果，"
            f"提供{'简要' if interpretation_depth == '简洁' else '详细' if interpretation_depth == '详细' else '深入'}的解读。"
        )
        
        if include_history:
            prompt += (
                "\n\n请包含一些关于这些符文的历史背景和北欧神话中的相关故事，"
                "特别是它们如何在这个十字布局中相互作用。"
            )
        
        yield event.request_llm(
            prompt=prompt,
            system_prompt=(
                "你是一个专业的卢恩符文占卜师，精通北欧神话和符文象征意义。"
                "请根据用户抽到的五个符文和问题，分析现状、挑战、建议、助力和可能的结果，"
                "提供专业且有洞察力的占卜解读。"
            )
        )
    
    async def nine_runes_divination(self, event: AstrMessageEvent, question: str, 
                                   interpretation_depth: str, include_history: bool):
        """九符文世界之树占卜法"""
        runes = self.draw_runes(9)
        reversed_status = [random.choice([True, False]) for _ in range(9)]
        
        # 世界之树的九个国度
        worlds = [
            "阿斯加德(神之国/最终结果)",
            "华纳海姆(华纳神族/情感关系)",
            "亚尔夫海姆(光之精灵/精神指引)",
            "米德加尔特(人类世界/现状)",
            "约顿海姆(巨人国度/挑战)",
            "瓦特阿尔海姆(黑暗精灵/物质基础)",
            "尼福尔海姆(雾之国/潜意识)",
            "穆斯贝尔海姆(火之国/创造力)",
            "赫尔海姆(死之国/隐藏力量)"
        ]
        
        # 先显示抽到的符文
        rune_display = "您在世界之树九个国度抽到的符文是:\n"
        for i, rune in enumerate(runes):
            rune_display += (
                f"{i+1}. {worlds[i]}: "
                f"{rune['symbol']} {rune['name']} ({'逆位' if reversed_status[i] else '正位'})\n"
            )
        yield event.plain_result(rune_display + "\n正在为您解读...")
        
        # 构建提示词
        prompt = (
            f"问题: {question}\n\n"
            f"九符文世界之树占卜结果:\n"
        )
        
        for i in range(9):
            prompt += (
                f"{i+1}. {worlds[i]}: {runes[i]['symbol']} {runes[i]['name']} "
                f"({'逆位' if reversed_status[i] else '正位'})\n"
            )
            
        prompt += (
            f"\n请根据这九个符文在世界之树九个国度中的位置和正逆位关系，"
            f"提供{'简要' if interpretation_depth == '简洁' else '详细' if interpretation_depth == '详细' else '深入'}的解读。"
        )
        
        if include_history:
            prompt += (
                "\n\n请包含一些关于这些符文的历史背景和北欧神话中的相关故事，"
                "特别是它们如何在世界之树的九个国度中相互作用。"
            )
        
        yield event.request_llm(
            prompt=prompt,
            system_prompt=(
                "你是一个专业的卢恩符文占卜师，精通北欧神话和符文象征意义。"
                "请根据用户抽到的九个符文在世界之树九个国度中的位置和问题，"
                "提供全面且深刻的占卜解读。"
            )
        )
    
    def draw_runes(self, count: int) -> List[Dict]:
        """随机抽取指定数量的符文"""
        return random.sample(RUNES, count)