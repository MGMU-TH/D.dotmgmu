import discord
from discord import app_commands
from discord.ext import commands
import requests
import json

# 1. ระบุ Web App URL จาก Google Apps Script ของคุณ
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby8dOo8WfSDhLR9nO88unOS7IKLWVE_UXeVL_YzBniM7M7UO_tQPRAhcyW38jVLtvpNIQ/exec"

# 2. ตั้งค่า Intents สำหรับ Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# ฟังก์ชันเชื่อมต่อกับ Google Apps Script API (CRUD)
# ---------------------------------------------------------
def call_api(action: str, payload: dict = None):
    """ฟังก์ชันกลางสำหรับส่งข้อมูลหา Google Sheets Web App"""
    try:
        params = {"action": action}
        if payload is None:
            payload = {}
        payload["action"] = action
        
        # ส่ง POST Request พร้อมข้อมูล JSON
        response = requests.post(WEB_APP_URL, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"API Error ({action}): {e}")
        return {"status": "error", "message": str(e)}

def get_config(key: str):
    """อ่านค่าจากชีท Setting"""
    try:
        res = requests.get(WEB_APP_URL, params={"action": "get_config", "key": key}, timeout=10)
        data = res.json()
        if data.get("status") == "success":
            return data.get("value")
    except Exception as e:
        print(f"Get Config Error: {e}")
    return None

def set_config(key: str, value: str, description: str = ""):
    """บันทึกค่าลงชีท Setting"""
    return call_api("set_config", {"key": key, "value": str(value), "description": description})

# ---------------------------------------------------------
# Event: บอทพร้อมทำงาน
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f'✅ บอทตื่นแล้ว! เข้าใช้งานในชื่อ: {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"🔄 ซิงค์คำสั่งแบบ Slash Command เรียบร้อยแล้ว ทั้งหมด {len(synced)} คำสั่ง")
    except Exception as e:
        print(f"❌ ซิงค์คำสั่งไม่สำเร็จ: {e}")

# ---------------------------------------------------------
# 1. คำสั่งทั่วไป & ระบบตั้งค่า
# ---------------------------------------------------------
@bot.tree.command(name="ping", description="เช็คความหน่วงของบอท")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(
        f"🏓 **Pong!** ความหน่วงบอทในขณะนี้: `{latency} ms`", 
        ephemeral=True
    )

@bot.tree.command(name="set_report_channel", description="กำหนดช่องสำหรับรับรายงานบั๊ก/ข้อผิดพลาด (แอดมิน)")
@app_commands.checks.has_permissions(administrator=True)
async def set_report_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    res = set_config("bug_report_channel_id", channel.id, "ช่องรายงานบั๊ก")
    if res.get("status") == "success":
        await interaction.response.send_message(
            f"✅ บันทึกช่อง {channel.mention} เป็นช่องรับแจ้งบั๊กเรียบร้อยครับ (บันทึกลง Google Sheets)",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("❌ เกิดข้อผิดพลาดในการบันทึกข้อมูล", ephemeral=True)

# ---------------------------------------------------------
# 2. ระบบยืนยันตัวตน Roblox (Roblox Verification)
# ---------------------------------------------------------
@bot.tree.command(name="verify", description="ผูกบัญชี Discord กับ Roblox Username")
async def verify(interaction: discord.Interaction, roblox_username: str):
    await interaction.response.defer(ephemeral=True)
    discord_id = str(interaction.user.id)
    
    # ส่งข้อมูลผูกบัญชีไปเก็บในชีท Setting (หรือย้ายไปชีทเฉพาะ)
    res = set_config(f"verify_{discord_id}", roblox_username, f"Roblox Username ของ {interaction.user.name}")
    if res.get("status") == "success":
        await interaction.followup.send(
            f"✅ ผูกบัญชีสำเร็จ! บัญชี Discord ของคุณถูกเชื่อมเข้ากับ Roblox: **{roblox_username}** เรียบร้อยแล้วครับ",
            ephemeral=True
        )
    else:
        await interaction.followup.send("❌ เกิดข้อผิดพลาดในการเชื่อมต่อข้อมูล", ephemeral=True)

# ---------------------------------------------------------
# 3. ระบบจัดการคลัง/ห้องหนังสือ (Books Sheet)
# ---------------------------------------------------------
@bot.tree.command(name="add_book", description="เพิ่มหนังสือ/ไอเทมใหม่ลงคลัง (แอดมิน)")
@app_commands.checks.has_permissions(administrator=True)
async def add_book(interaction: discord.Interaction, book_id: str, title: str, category: str, total_copies: int):
    await interaction.response.defer(ephemeral=True)
    payload = {
        "book_id": book_id,
        "title": title,
        "category": category,
        "total_copies": total_copies,
        "available_copies": total_copies
    }
    res = call_api("add_book", payload)
    if res.get("status") == "success":
        await interaction.followup.send(f"📚 เพิ่มหนังสือ **{title}** (ID: `{book_id}`) ลงในคลังเรียบร้อยครับ", ephemeral=True)
    else:
        await interaction.followup.send("❌ เกิดข้อผิดพลาดในการเพิ่มหนังสือ", ephemeral=True)

@bot.tree.command(name="list_books", description="ดูรายการหนังสือทั้งหมดในคลัง")
async def list_books(interaction: discord.Interaction):
    await interaction.response.defer()
    res = call_api("get_books")
    if res.get("status") == "success":
        books = res.get("data", [])
        if not books:
            await interaction.followup.send("📑 ยังไม่มีรายการหนังสือในคลังครับ")
            return
        
        embed = discord.Embed(title="📚 รายการหนังสือ/เอกสารในคลัง", color=discord.Color.blue())
        for b in books[:10]: # แสดงผลไม่เกิน 10 รายการ
            embed.add_field(
                name=f"{b.get('title')} (ID: {b.get('book_id')})",
                value=f"หมวดหมู่: {b.get('category')} | คงเหลือ: {b.get('available_copies')}/{b.get('total_copies')}",
                inline=False
            )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ ไม่สามารถดึงข้อมูลคลังหนังสือได้")

# ---------------------------------------------------------
# 4. ระบบรับสมัครเรียน / ยื่นใบสมัคร (Admissions Sheet)
# ---------------------------------------------------------
@bot.tree.command(name="apply_school", description="ส่งใบสมัครเข้าศึกษา/ลงทะเบียน")
async def apply_school(interaction: discord.Interaction, roblox_name: str, faculty_or_class: str, note: str = "-"):
    await interaction.response.defer(ephemeral=True)
    payload = {
        "discord_id": str(interaction.user.id),
        "discord_name": interaction.user.name,
        "roblox_name": roblox_name,
        "faculty": faculty_or_class,
        "note": note,
        "status": "Pending"
    }
    res = call_api("submit_application", payload)
    if res.get("status") == "success":
        await interaction.followup.send(
            f"📝 ส่งใบสมัครของคุณเรียบร้อยแล้วครับ!\n• Roblox: **{roblox_name}**\n• คณะ/สายชั้น: **{faculty_or_class}**\nสถานะปัจจุบัน: `Pending (รอการตรวจสอบ)`",
            ephemeral=True
        )
    else:
        await interaction.followup.send("❌ เกิดข้อผิดพลาดในการส่งใบสมัคร", ephemeral=True)

# ---------------------------------------------------------
# 5. ระบบแจ้งรายงานบั๊ก (Report Bug System)
# ---------------------------------------------------------
@bot.tree.command(name="report_bug", description="รายงานข้อผิดพลาดหรือบั๊กในเกม/ระบบ")
async def report_bug(interaction: discord.Interaction, title: str, description: str):
    await interaction.response.defer(ephemeral=True)
    
    # ดึง ID ของช่องรายงานบั๊กจาก Google Sheets
    target_channel_id = get_config("bug_report_channel_id")
    
    embed = discord.Embed(title=f"🐛 รายงานบั๊ก: {title}", color=discord.Color.red())
    embed.add_field(name="รายละเอียด", value=description, inline=False)
    embed.set_footer(text=f"แจ้งโดย: {interaction.user.name} ({interaction.user.id})")
    
    if target_channel_id:
        try:
            channel = bot.get_channel(int(target_channel_id))
            if channel:
                await channel.send(embed=embed)
                await interaction.followup.send("✅ ส่งรายงานข้อผิดพลาดไปยังทีมงานเรียบร้อยแล้วครับ ขอบคุณครับ!", ephemeral=True)
                return
        except Exception as e:
            print(f"Send bug report error: {e}")
            
    await interaction.followup.send("✅ รับข้อมูลรายงานบั๊กเรียบร้อยแล้วครับ (แต่ยังไม่ได้ตั้งค่าช่องรับแจ้ง)", ephemeral=True)

# ---------------------------------------------------------
# ใส่ Discord Bot Token ของคุณที่นี่
# ---------------------------------------------------------
BOT_TOKEN = "ใส่_DISCORD_BOT_TOKEN_ของนายตรงนี้"

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
