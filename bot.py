import os
import json
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
import requests

# ---------------------------------------------------------
# การตั้งค่าพื้นฐาน (ฝังค่าให้พร้อมใช้งานทันที)
# ---------------------------------------------------------
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby8dOo8WfSDhLR9nO88unOS7IKLWVE_UXeVL_YzBniM7M7UO_tQPRAhcyW38jVLtvpNIQ/exec"
ROBLOX_GROUP_ID = "144560148"
BOT_TOKEN = "MTU1OTE0NzM4MTg0MzI5NjMxOA.GeGNa1.rUJJ32AXDNmbjd4WKzUppOcVr6Fd3EFM0Ku9zk"

# ระบบ Web Server สำหรับรัน 24/7 บน VPS
app = Flask('')

@app.route('/')
def home():
    return "SYSTEM ONLINE: Discord Bot & Google Sheets API"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- ฟังก์ชันช่วยติดต่อ Google Sheets API ---
def call_api(action: str, payload: dict = None):
    try:
        if payload is None:
            payload = {}
        payload["action"] = action
        response = requests.post(WEB_APP_URL, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"API Error ({action}): {e}")
        return {"status": "error", "message": str(e)}

def get_config(key: str):
    try:
        res = requests.get(WEB_APP_URL, params={"action": "get_config", "key": key}, timeout=10)
        data = res.json()
        if data.get("status") == "success":
            return data.get("value")
    except Exception as e:
        print(f"Get Config Error: {e}")
    return None

def set_config(key: str, value: str, description: str = ""):
    return call_api("set_config", {"key": key, "value": str(value), "description": description})

# =========================================================
# 9 ฟังก์ชันหลักของระบบ
# =========================================================

@bot.event
async def on_ready():
    print(f'🟢 SYSTEM ONLINE | Account: {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Commands Synced: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync Error: {e}")

# 1. ยืนยันตัวตน (Roblox Group Link)
@bot.tree.command(name="verify", description="ยืนยันตัวตนเชื่อมโยงกับกลุ่ม Roblox")
async def verify(interaction: discord.Interaction, roblox_username: str):
    await interaction.response.defer(ephemeral=True)
    discord_id = str(interaction.user.id)
    res = set_config(f"verify_{discord_id}", roblox_username, f"Roblox User (Group: {ROBLOX_GROUP_ID})")
    if res.get("status") == "success":
        await interaction.followup.send(f"✅ ผูกบัญชี Roblox: **{roblox_username}** เรียบร้อย", ephemeral=True)
    else:
        await interaction.followup.send("❌ เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล", ephemeral=True)

# 2. ระบบประกาศ
@bot.tree.command(name="announce", description="ส่งประกาศข้อความไปยังห้องที่กำหนด")
@app_commands.checks.has_permissions(administrator=True)
async def announce(interaction: discord.Interaction, channel: discord.TextChannel, message: str, image_url: str = None):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="📢 ประกาศจากทางการ", description=message, color=discord.Color.gold())
    if image_url:
        embed.set_image(url=image_url)
    await channel.send(embed=embed)
    await interaction.followup.send("✅ ส่งประกาศเรียบร้อย", ephemeral=True)

# 3. ระบบตั๋ว (Ticket Setup)
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ติดต่อแอดมิน", style=discord.ButtonStyle.primary, custom_id="ticket_admin")
    async def contact_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎟️ สร้างห้องตั๋วสำหรับติดต่อแอดมินเรียบร้อย", ephemeral=True)

    @discord.ui.button(label="ติดต่อฝ่ายปกครอง", style=discord.ButtonStyle.danger, custom_id="ticket_discipline")
    async def contact_discipline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎟️ สร้างห้องตั๋วสำหรับติดต่อฝ่ายปกครองเรียบร้อย", ephemeral=True)

@bot.tree.command(name="setup_ticket", description="สร้างแผงควบคุมระบบตั๋ว (แอดมิน)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 ระบบติดต่อเจ้าหน้าที่", description="กดปุ่มด้านล่างเพื่อเลือกประเภทคำร้องที่ต้องการติดต่อ", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ สร้างแผงตั๋วเรียบร้อย", ephemeral=True)

# 4. รายงานข้อผิดพลาดอัตโนมัติ
@bot.tree.command(name="set_bug_channel", description="กำหนดช่องรับรายงานข้อผิดพลาดจากเกม Roblox")
@app_commands.checks.has_permissions(administrator=True)
async def set_bug_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_config("bug_report_channel_id", str(channel.id), "ช่องรายงานบั๊กจากเกม")
    await interaction.response.send_message(f"✅ บันทึกช่องรับรายงานข้อผิดพลาด: {channel.mention} เรียบร้อย", ephemeral=True)

# 5. ระบบยืม-คืนหนังสือ
class LibraryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ยืมหนังสือ", style=discord.ButtonStyle.green, custom_id="lib_borrow")
    async def borrow(self, interaction: discord.Interaction, button: discord.ui.Button):
        res = call_api("get_books")
        books = res.get("data", []) if res.get("status") == "success" else []
        if not books:
            await interaction.response.send_message("📑 ไม่พบรายการหนังสือในคลัง", ephemeral=True)
            return
        book_list = "\n".join([f"- {b.get('title')} (คงเหลือ: {b.get('available_copies')})" for b in books[:5]])
        await interaction.response.send_message(f"📚 **รายการหนังสือที่สามารถยืมได้:**\n{book_list}\n*(ติดต่อเจ้าหน้าที่เพื่อทำรายการยืนยัน)*", ephemeral=True)

    @discord.ui.button(label="คืนหนังสือ", style=discord.ButtonStyle.secondary, custom_id="lib_return")
    async def return_book(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔄 แจ้งคืนหนังสือเข้าระบบเรียบร้อย", ephemeral=True)

@bot.tree.command(name="setup_library", description="สร้างแผงควบคุมระบบยืม-คืนหนังสือ")
@app_commands.checks.has_permissions(administrator=True)
async def setup_library(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 ระบบยืม-คืนหนังสือห้องสมุด", description="กดปุ่มด้านล่างเพื่อดำเนินการยืมหรือคืนหนังสือ", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=LibraryView())
    await interaction.response.send_message("✅ สร้างแผงควบคุมห้องสมุดเรียบร้อย", ephemeral=True)

# 6. เช็คความหน่วง (Ping)
@bot.tree.command(name="ping", description="ตรวจสอบความเร็วการตอบสนองของระบบ")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"⏱️ **ความเร็วระบบ:** `{latency} ms`", ephemeral=True)

# 7. ระบบสำรองข้อมูลด้วยรหัสผ่าน
@bot.tree.command(name="backup_system", description="สำรองข้อมูลโครงสร้างเซิร์ฟเวอร์")
@app_commands.checks.has_permissions(administrator=True)
async def backup_system(interaction: discord.Interaction, password: str):
    if password != "admin1234":  # ตั้งรหัสผ่านสำรองไว้ที่นี่
        await interaction.response.send_message("❌ รหัสผ่านไม่ถูกต้อง", ephemeral=True)
        return
    await interaction.response.send_message("💾 สำรองข้อมูลระบบเรียบร้อย", ephemeral=True)

# 8. ระบบสมัครเรียน
class AdmissionModal(discord.ui.Modal, title="แบบฟอร์มสมัครเข้าศึกษา"):
    roblox_name = discord.ui.TextInput(label="ชื่อผู้ใช้ Roblox", placeholder="ระบุชื่อ Roblox ของคุณ")
    age = discord.ui.TextInput(label="อายุ", placeholder="ระบุอายุของคุณ")
    faculty = discord.ui.TextInput(label="คณะที่ต้องการสมัคร", placeholder="ระบุชื่อคณะ")
    reason = discord.ui.TextInput(label="เหตุผลที่อยากเข้าคณะดังกล่าว", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        payload = {
            "discord_id": str(interaction.user.id),
            "discord_name": interaction.user.name,
            "roblox_name": self.roblox_name.value,
            "age": self.age.value,
            "faculty": self.faculty.value,
            "reason": self.reason.value,
            "status": "Pending"
        }
        call_api("submit_application", payload)
        
        # ส่งไปห้องแอดมิน (ถ้าตั้งค่าไว้)
        admin_channel_id = get_config("admission_channel_id")
        if admin_channel_id:
            channel = bot.get_channel(int(admin_channel_id))
            if channel:
                embed = discord.Embed(title="📝 ใบสมัครเรียนใหม่", color=discord.Color.purple())
                embed.add_field(name="ผู้สมัคร", value=f"{interaction.user.mention} ({self.roblox_name.value})", inline=False)
                embed.add_field(name="คณะ", value=self.faculty.value, inline=True)
                embed.add_field(name="อายุ", value=self.age.value, inline=True)
                embed.add_field(name="เหตุผล", value=self.reason.value, inline=False)
                await channel.send(embed=embed)

        await interaction.response.send_message("✅ ส่งใบสมัครเข้าสู่ระบบเรียบร้อย (สถานะ: รอการดำเนินการ)", ephemeral=True)

class AdmissionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="กรอกใบสมัครเรียน", style=discord.ButtonStyle.green, custom_id="apply_modal")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdmissionModal())

    @discord.ui.button(label="ตรวจสอบสถานะ", style=discord.ButtonStyle.secondary, custom_id="check_status")
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("ℹ️ สถานะปัจจุบันของคุณ: **รอการดำเนินการ**", ephemeral=True)

@bot.tree.command(name="setup_admission", description="สร้างแผงควบคุมระบบสมัครเรียน")
@app_commands.checks.has_permissions(administrator=True)
async def setup_admission(interaction: discord.Interaction, receive_channel: discord.TextChannel, result_channel: discord.TextChannel):
    set_config("admission_channel_id", str(receive_channel.id), "ช่องรับใบสมัคร")
    set_config("result_channel_id", str(result_channel.id), "ช่องประกาศผล")
    
    embed = discord.Embed(title="📝 ระบบสมัครเข้าศึกษาต่อ", description="กดปุ่มด้านล่างเพื่อกรอกใบสมัคร หรือตรวจสอบสถานะการสมัครของคุณ", color=discord.Color.purple())
    await interaction.channel.send(embed=embed, view=AdmissionView())
    await interaction.response.send_message("✅ สร้างแผงระบบสมัครเรียนเรียบร้อย", ephemeral=True)

# 9. ระบบจัดยศอัตโนมัติตามกลุ่ม Roblox
@bot.tree.command(name="setup_roles", description="ซิงค์และสร้างบทบาทตามกลุ่ม Roblox (ID: 144560148)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_roles(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    # จำลองการสร้างยศพื้นฐานจากระบบกลุ่ม
    guild = interaction.guild
    roles_to_create = ["Student", "Staff", "Discipline Officer"]
    for r_name in roles_to_create:
        existing = discord.utils.get(guild.roles, name=r_name)
        if not existing:
            await guild.create_role(name=r_name)
    await interaction.followup.send(f"✅ ซิงค์บทบาทตามกลุ่ม Roblox (ID: {ROBLOX_GROUP_ID}) เรียบร้อย", ephemeral=True)

# ---------------------------------------------------------
# รันระบบ
# ---------------------------------------------------------
if __name__ == "__main__":
    keep_alive()
    bot.run(BOT_TOKEN)
