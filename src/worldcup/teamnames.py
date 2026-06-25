"""世界杯 2026 球队名映射:The Odds API 英文名 <-> 中文名(模型/战绩用) <-> slug。

odds.json 用英文名,战绩/DC 模型用中文名,docs 文件用 slug。本表打通三者。
"""

# 中文名 -> slug(全 48 队)
ZH_TO_SLUG = {
    "墨西哥": "moxige1", "韩国": "hanguo1", "捷克": "jieke1", "南非": "nanfei",
    "加拿大": "jianada1", "瑞士": "ruishi", "波黑": "bohei1", "卡塔尔": "kataer1",
    "巴西": "baxi1", "摩洛哥": "moluoge", "苏格兰": "sugelan", "海地": "haidi",
    "美国": "meiguo1", "澳大利亚": "aodaliya1", "巴拉圭": "balagui", "土耳其": "tuerqi1",
    "德国": "deguo1", "科特迪瓦": "ketediwa1", "厄瓜多尔": "eguaduoer", "库拉索": "kulasuo",
    "荷兰": "helan1", "日本": "riben1", "瑞典": "ruidian1", "突尼斯": "tunisi1",
    "埃及": "aiji1", "伊朗": "yilang1", "比利时": "bilishi1", "新西兰": "xinxilan1",
    "西班牙": "xibanya1", "乌拉圭": "wulagui", "佛得角": "fodejiao1", "沙特阿拉伯": "shatealabo",
    "法国": "faguo1", "挪威": "nuowei", "塞内加尔": "saineijiaer", "伊拉克": "yilake1",
    "阿根廷": "agenting", "奥地利": "aodili", "阿尔及利亚": "aerjiliya", "约旦": "yuedan1",
    "哥伦比亚": "gelunbiya", "葡萄牙": "putaoya", "民主刚果": "minzhugangguo",
    "乌兹别克斯坦": "wuzibiekesitan", "英格兰": "yinggelan", "加纳": "jiana1",
    "克罗地亚": "keluodiya1", "巴拿马": "banama",
}

# The Odds API 英文名 -> 中文名(全 48 队;含当前盘口里出现的 38 队 + 其余 10 队)
EN_TO_ZH = {
    "Mexico": "墨西哥", "South Korea": "韩国", "Korea Republic": "韩国",
    "Czechia": "捷克", "Czech Republic": "捷克", "South Africa": "南非",
    "Canada": "加拿大", "Switzerland": "瑞士",
    "Bosnia and Herzegovina": "波黑", "Bosnia & Herzegovina": "波黑", "Qatar": "卡塔尔",
    "Brazil": "巴西", "Morocco": "摩洛哥", "Scotland": "苏格兰", "Haiti": "海地",
    "USA": "美国", "United States": "美国", "Australia": "澳大利亚", "Paraguay": "巴拉圭",
    "Turkey": "土耳其", "Türkiye": "土耳其", "Germany": "德国",
    "Ivory Coast": "科特迪瓦", "Côte d'Ivoire": "科特迪瓦", "Ecuador": "厄瓜多尔",
    "Curaçao": "库拉索", "Curacao": "库拉索", "Netherlands": "荷兰", "Japan": "日本",
    "Sweden": "瑞典", "Tunisia": "突尼斯", "Egypt": "埃及", "Iran": "伊朗",
    "Belgium": "比利时", "New Zealand": "新西兰", "Spain": "西班牙", "Uruguay": "乌拉圭",
    "Cape Verde": "佛得角", "Cabo Verde": "佛得角", "Saudi Arabia": "沙特阿拉伯",
    "France": "法国", "Norway": "挪威", "Senegal": "塞内加尔", "Iraq": "伊拉克",
    "Argentina": "阿根廷", "Austria": "奥地利", "Algeria": "阿尔及利亚", "Jordan": "约旦",
    "Colombia": "哥伦比亚", "Portugal": "葡萄牙",
    "DR Congo": "民主刚果", "Congo DR": "民主刚果", "Democratic Republic of the Congo": "民主刚果",
    "Uzbekistan": "乌兹别克斯坦", "England": "英格兰", "Ghana": "加纳",
    "Croatia": "克罗地亚", "Panama": "巴拿马",
}


def en_to_zh(name):
    """英文队名 -> 中文名;未知返回 None。"""
    return EN_TO_ZH.get(name)


def zh_to_slug(name):
    """中文队名 -> slug;未知返回 None。"""
    return ZH_TO_SLUG.get(name)
